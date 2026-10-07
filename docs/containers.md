# Application containers

## Status and assumptions

Build, Linux runtime, HTTP endpoint, and container-replacement persistence checks
passed on 7 October 2026. Validation used Docker Engine 29.8.1,
Compose 5.5.1, Python 3.12.14, PyTorch 2.8.0+cpu (no CUDA), libsndfile 1.2.2,
and Gunicorn 23.0.0. The tested image is `speech-rec-backend:local`.
Its application/configuration source hashes matched the workspace. Base image tags
and transitive dependencies can change; future builds need their own validation.

The validated target is a Linux container on an x86-64 Docker engine with the Compose
plugin, CPU inference, one backend replica, and enough RAM/disk for PyTorch and cached
Whisper assets. Other architectures are unverified. Use Docker Desktop in Linux
container mode on Windows. Docker installation is a host prerequisite, separate
from Python virtual-environment setup.

The backend uses one Gunicorn `gthread` worker with four threads. The inference
lock still permits only one decode/inference at a time; other threads can serve
health/list/search or return `service_busy`. Do not increase workers or replicas
without redesigning shared capacity handling and checking SQLite concurrency.
See [Gunicorn's thread design](https://docs.gunicorn.org/en/stable/design.html).

## Build and start

If Docker was just installed and this terminal cannot find `docker` or
`docker-credential-desktop`, reopen the terminal so it inherits the new PATH.
If either command is still unavailable, check that your Docker installation's
CLI directory is on PATH, including its credential helper. Installation paths
vary by operating system and installation method; use your actual installation
location. Do not disable credential handling to work around a missing helper.

From the repository root, once Docker is installed and running:

```powershell
docker version
docker compose version
docker compose config
docker compose up -d --build
docker compose logs -f backend frontend
```

Exit log following with Ctrl+C; this leaves the container running. Build needs
access to the Python/Node/Nginx image registry, npm, Debian package repositories, PyPI, and the
official [PyTorch CPU wheel index](https://docs.pytorch.org/get-started/previous-versions/).
CPU PyTorch is installed before the common runtime requirements to avoid bringing
CUDA libraries into the image. No local `.venv` is copied or needed in the image.

The first start downloads model assets from Hugging Face into the persistent model
volume. Subsequent starts reuse them. The Windows model cache is not automatically
imported. The Dockerfile grants a ten-minute health-check start period for first
loading; that is a grace period, not proof that loading completes within it.

```powershell
docker compose ps
curl.exe http://127.0.0.1:8000/health
```

Wait for ready health before uploading. If model loading fails, logs explain the
failure and `/health` reports unavailable. Correct network/configuration problems,
then use `docker compose restart backend` to retry startup. An unhealthy status
does not itself trigger a Docker restart; `unless-stopped` acts on process exit.

## Ports and configuration

Compose publishes the frontend at `127.0.0.1:3000` and the direct backend API
at `127.0.0.1:8000`, forwarding to backend container port 5000. This
coexists with the native development server on host port 5000. The application
binds to all interfaces *inside* the container; the host mapping remains local.

| Setting | Container value | Purpose |
| --- | --- | --- |
| `DATABASE_PATH` | `/data/transcriptions.sqlite3` | Persistent SQLite file |
| `UPLOAD_DIR` | `/data/uploads` | Persistent recordings |
| `MODEL_CACHE_DIR` | `/models` | Persistent Hugging Face model cache |
| `PORT` | `5000` | Gunicorn and readiness probe port |
| `MAX_CONTENT_LENGTH` | `26214400` | Full request limit (25 MiB) |
| `MAX_AUDIO_DURATION_SECONDS` | `600` | Decoded-audio limit |

Compose sets these variables explicitly. Host `backend/.env` is excluded from the
image and is not loaded by this Compose file. Change values in Compose or a local
Compose override. If changing the internal port, also update the port mapping.
The Flask development `HOST` setting is not used by Gunicorn.

To point the React dev server at the container, set this in `frontend/.env` and
restart Vite:

```dotenv
BACKEND_URL=http://127.0.0.1:8000
```

The frontend has its own image: Node 24 installs the lockfile dependencies, runs
UI tests, and builds React; Nginx 1.28 serves only the resulting static files.
The runtime runs as the non-root `nginx` user. Node, source files, host `.env`, and
`node_modules` are not included in the runtime image. No public deployment, TLS
termination, or user authentication is included.

### Frontend routing and assumptions

Open `http://127.0.0.1:3000` for the application. Nginx forwards `/health`,
`/transcribe`, `/transcriptions`, and `/search` to `backend:5000`, preserving
query strings. This same-origin routing needs no CORS or `BACKEND_URL` setting.
The optional Vite `.env` setting above applies only to native development.

Compose waits for backend readiness before starting the frontend using
[`service_healthy`](https://docs.docker.com/compose/how-tos/startup-order/).
The frontend's own `/frontend-health` checks Nginx availability; `/health`
checks backend/model readiness. A healthy frontend alone does not prove inference
is available. If initial model loading fails, inspect backend logs, correct the
cause, restart the backend, and run `docker compose up -d` again.

Nginx uses Docker DNS with a ten-second cache so backend replacement can recover
without rebuilding/restarting the frontend. Temporary requests during replacement
can fail. The [proxy configuration](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)
disables upstream retries to avoid duplicating uploads after an ambiguous failure.
Connection failures and timeouts return a JSON 503; refresh the list before retrying.

The proxy and Flask both default to a 25 MiB full-request limit. If changing the
backend limit, change `client_max_body_size` and its JSON message in
`frontend/nginx.conf` and rebuild the frontend. Proxy read/send timeouts are 660
seconds of inactivity, not a guaranteed total processing deadline. This assumes
local, synchronous CPU inference; long recordings still need capacity measurement.
SPA routes fall back to `index.html`; missing assets return 404. HTML is revalidated,
while content-hashed assets are cached for one year. Frontend changes require a
rebuild (`docker compose up -d --build frontend`). No source is bind-mounted.

## Persistence and permissions

Compose creates two project-scoped named volumes: `transcription-data` for SQLite
and uploads, and `whisper-models` for weights. Keep the same Compose project name
and directory when replacing containers, or explicitly reuse the existing volume
names. Moving/renaming the project may select new empty volumes.

The image runs as UID/GID 10001. Data/model directories are initialized with that
ownership. Docker populates new empty named volumes from these image directories;
see [Docker volume behavior](https://docs.docker.com/engine/storage/volumes/).
Existing volumes or host bind mounts must already be writable by this UID. This
permission behavior passed locally for newly created named volumes: the process
ran as UID/GID 10001 and could write to both `/data` and `/models`.

Stop both services with `docker compose stop`. `docker compose down` removes
containers and the network while retaining named volumes. Do not use the volume
removal option or prune these volumes unless intentionally deleting the stored
recordings, database, and model cache. Back up persistent data before migration.

## Repeatable validation

The repeatable HTTP check can also be run from `backend/` using the documented
Python environment (requires `requests`, already a runtime dependency):

```powershell
.venv/Scripts/python.exe -m scripts.validate_container before
# From the repository root, replace the container:
docker compose up -d --no-build --force-recreate backend
# Once healthy, from backend/:
.venv/Scripts/python.exe -m scripts.validate_container after
```

The script uses uniquely tagged sample filenames and saves a local comparison
record to ignored `backend/data/container-validation.json`. It retains its four
test transcriptions in the container volume to establish persistence. It also
checks malformed, empty, unsupported, undecodable, and oversized requests. Do not
run it against an unrelated service; its default target is local port 8000.

Recordings are not included in a clone. Obtain the three validation MP3s
separately and place them in the repository root for these examples, or pass
`--sample-dir` to the Python validation command. Automated unit/component tests
do not require these recordings. With the samples available:

```powershell
curl.exe -f http://127.0.0.1:8000/health
curl.exe -f -F "file=@Sample 1.mp3" http://127.0.0.1:8000/transcribe
curl.exe -f -F "file=@Sample 2.mp3" http://127.0.0.1:8000/transcribe
curl.exe -f -F "file=@Sample 3.mp3" http://127.0.0.1:8000/transcribe
curl.exe -f -F "file=@Sample 1.mp3" http://127.0.0.1:8000/transcribe
curl.exe -f http://127.0.0.1:8000/transcriptions
curl.exe -f --get --data-urlencode "filename=sample 1" http://127.0.0.1:8000/search
```

Confirm four 201 responses with nonempty text, distinct filenames/IDs for the
duplicate, and two matching search records on initially empty storage. Record
the IDs, then replace the container without removing volumes:

```powershell
docker compose up -d --force-recreate backend
docker compose ps
curl.exe -f http://127.0.0.1:8000/health
curl.exe -f http://127.0.0.1:8000/transcriptions
docker compose exec backend sh -c 'id; ls -l /data/uploads; ls -ld /models'
```

Wait for healthy state again. Check that the same IDs and all stored files remain,
and that cached loading works without a repeated weights download. Verify invalid
and oversized uploads return the documented JSON errors. These operations add
sample records to the container database; they are not automatic cleanup tests.

### Recorded results (7 October 2026)

- Compose configuration and image build passed; in-image `pip check` reported no
  broken requirements. The running service became healthy at localhost:8000.
- All three supplied samples plus Sample 1 again returned 201 with nonempty text
  and four distinct stored filenames. Listing and full/partial/no-match searches passed.
- Missing file field, empty audio, unsupported format, corrupt MP3, and a request
  over 25 MiB returned the expected JSON 400/415/413 errors.
- `--force-recreate --no-build` changed the container ID. All four records,
  including IDs and text, remained identical. SHA-256 comparisons of all files
  under `/data/uploads` and `/models` were identical before and after replacement.
- The replacement became healthy using the retained model cache. Four audio files
  remained, with no additional files from rejected requests. Test records are
  intentionally retained; comparison evidence is ignored under `backend/data/`.

These checks validate this local single-instance setup. They do not establish
recognition accuracy, other CPU architectures, or production throughput.

Gunicorn's 600-second timeout is worker-liveness tolerance, not a strict request
deadline with threaded workers. Its graceful shutdown timeout is also 600 seconds;
Compose waits 610 seconds before force termination. These conservative values are
provisional until measured in-container with longer recordings. The prior local
1–2 second sample timings are not container benchmarks. Abrupt termination may
leave an orphan upload as described in the root README.

### Changing the browser port

Host port 3000 is the default; the frontend listens on 8080 inside its container.
If the host port is occupied or blocked, set `FRONTEND_PORT` before starting:

```powershell
$env:FRONTEND_PORT = '3001'
docker compose up -d
```

Then open `http://127.0.0.1:3001`. This changes only the host mapping; the frontend
API proxy still uses the Compose service name and internal backend port.

## Frontend container validation (7 October 2026)

- Multi-stage image build passed with Node 24, Vitest 4.1.11 (five tests), and
  Vite 7.3.6. Nginx 1.28.3 runs as UID/GID 101. Configuration validation passed.
- Updated the test/build lockfile after npm reported advisories in development
  dependencies. The final image build reported zero known npm vulnerabilities.
  This is a point-in-time dependency audit, not a complete container security audit.
- HTML, JS/CSS assets, asset cache headers, missing-asset 404, SPA fallback, and
  frontend health passed. The runtime contains neither Node nor the host `.env`.
- All three samples plus a duplicate passed through the Nginx proxy, as did full,
  partial, no-match searches and malformed/empty/unsupported/corrupt/oversized
  upload errors. Oversized uploads return JSON 413 at the proxy boundary.
- During a stopped-backend check, the frontend stayed available and API requests
  returned JSON 503. Backend replacement preserved all four comparison records;
  the unchanged frontend container reconnected and both services became healthy.
- The completed smoke run retained four tagged records. An earlier diagnostic run
  also retained four successful uploads before exposing the proxy 413 formatting
  issue, which was then fixed. Test recordings remain in the existing data volume.

Repeat the HTTP checks through the frontend from `backend/` (requires the optional
Python environment and separately supplied sample recordings):

```powershell
.venv/Scripts/python.exe -m scripts.validate_container before --url http://127.0.0.1:3000 --state data/frontend-container-validation.json
# From repository root: docker compose up -d --no-build --force-recreate backend
# Wait for /health on port 3000 to return 200, then from backend/:
.venv/Scripts/python.exe -m scripts.validate_container after --url http://127.0.0.1:3000 --state data/frontend-container-validation.json
```

Manual browser upload/list/search can be checked without any host Python setup.
Other CPU architectures and production throughput remain unverified.
