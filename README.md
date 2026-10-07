## Reviewer quick start (Docker)

Install Git and Docker with Linux containers and the Compose plugin. 
No host Python or Node.js installation is needed to run the full application.

```powershell
git clone https://github.com/SimJiaYewGit/SpeechRecognition.git
cd SpeechRecognition
docker compose up -d --build
docker compose ps
```

The first build downloads dependencies, and the backend downloads Whisper model
assets on its first start. The frontend starts after backend health is ready.
Open **http://127.0.0.1:3000** once both services are running. Upload your own MP3,
inspect the transcript, upload it again to check duplicate handling, and search
by filename. Private sample recordings are not included in the repository.

```powershell
curl.exe http://127.0.0.1:3000/health
docker compose logs --tail 50 backend frontend
# Stop the application while preserving records and model files:
docker compose down
```

Do not add `-v` to the shutdown command unless you intend to delete the persistent
volumes. A subsequent `docker compose up -d` reuses the images and saved data.
The frontend image build runs the three UI tests and production build. Proxy
upload/search/error handling and backend-replacement recovery were verified. Backend
unit tests are separate; see Tests and validation for the Python setup and commands.
See [docs/containers.md](docs/containers.md) for ports, proxy behavior, and limits.

## Project layout

- `backend/app/__init__.py`: Flask application factory.
- `backend/app/config.py`: environment and local configuration loading.
- `backend/app/routes.py`: endpoints, request validation, and JSON error handling.
- `backend/app/database.py`: SQLite initialization, record insertion, listing, and search.
- `backend/app/storage.py`: exclusive file creation and transcription/persistence workflow.
- `backend/app/audio.py`: MP3 decoding, duration validation, mono conversion, and resampling.
- `backend/app/transcription.py`: model readiness, loading, and serialized CPU inference.
- `backend/app/transcribe_files.py`: command-line sample validation.
- `backend/tests/`: backend test location.
- `backend/scripts/validate_samples.py`: optional real-model API validation.
- `backend/Dockerfile`, `backend/gunicorn.conf.py`: Linux production image and server configuration.
- `compose.yaml`: frontend/backend services with persistent backend data and model volumes.
- `frontend/Dockerfile`, `frontend/nginx.conf`: React build and static-serving/API proxy image.
- `frontend/src/components/`: upload and transcript display components.
- `frontend/src/api/`: shared backend request helpers.
- `frontend/src/tests/`: frontend test location.
- `architecture.pdf`: architecture diagram, assumptions, and validation limits.
- `docs/architecture.mmd`, `docs/build_architecture.py`: editable diagram and PDF sources.

See `project_guidelines.md` for the full plan and completion criteria.

## Local setup

Use 64-bit Python 3.12 for the validated setup and Node.js 22.12+ or 24.
Python 3.11 is a proposed alternative, but has not been tested here. Validation
used Windows, Python 3.12.14, and Node.js 24.14.0; other platforms remain unverified.
The Python dependencies include the CPU inference runtime and audio decoder.
Flask setup follows its [installation guide](https://flask.palletsprojects.com/en/stable/installation/).
Vite's runtime requirements are documented in its [getting started guide](https://vite.dev/guide/).

### Backend (PowerShell, from the repository root)

```powershell
py -3.12 -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements-dev.txt
backend/.venv/Scripts/python.exe -m pip check
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
Set-Location backend
.venv/Scripts/python.exe -m app
```

Install a 64-bit Python 3.12 interpreter first if `py -3.12 --version` fails.
If the interpreter is on PATH without the Windows launcher, use
`python -m venv backend/.venv` after confirming `python --version` is 3.12.
Use the virtual environment's Python for every install, test, and run command;
this avoids accidentally installing packages into a different interpreter.
`requirements-dev.txt` includes the runtime dependencies plus pytest. For a
runtime-only environment use `requirements.txt` instead. The copy command
preserves existing local configuration.

Activation is optional because the commands use the environment explicitly.
From the repository root, `.\\backend\\.venv\\Scripts\\Activate.ps1` enables bare
`python` commands; run `deactivate` when finished. If PowerShell blocks activation,
use the explicit executable paths above instead of changing execution policy.

On macOS/Linux, the equivalent setup uses `python3.12 -m venv backend/.venv`,
`backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt`, and
then `cd backend` followed by `.venv/bin/python -m app`. These platform commands
are documented for portability but have not been exercised in this project.
An MP3-capable libsndfile is required if no compatible SoundFile wheel is available.

The development server defaults to `http://127.0.0.1:5000`. Creating the app
initializes the SQLite schema and upload directory. `python -m app` also loads
Whisper before serving, trying the local cache first and downloading assets if
needed. If loading fails, the server starts with `/health` returning 503; listing
and search still work when the database is accessible. Restart after fixing the
dependency problem to retry model loading. Plain `create_app()` stays model-free
for tests; serving code should use `create_app(load_model=True)`.

Create a fresh `.venv` from an installed Python interpreter on each computer;
do not copy an existing environment. Reinstall the documented requirements.
If the base interpreter moves, stop backend processes and recreate the environment.
Keep `backend/data` and `backend/.cache` when rebuilding it to preserve recordings,
SQLite data, and downloaded models. `.venv` and `.env` are excluded from Git.

Initial package installation and first model loading need network access and
several hundred megabytes of downloads, with additional disk space for installed
packages and cached files. Model weights are separate from pip dependencies.
No CUDA setup is required: inference explicitly uses CPU. Direct Python package
versions are pinned, but transitive dependencies are not fully locked; the checked
environment and `pip check` results establish compatibility only for this run.

### Environment troubleshooting

| Symptom | Check or action |
| --- | --- |
| `python`/`py` missing | Install Python 3.12 or use a verified full interpreter path; confirm its version before creating the venv. |
| `ModuleNotFoundError` | Install the appropriate requirements file with `backend/.venv/Scripts/python.exe -m pip`, not global pip. |
| Missing pytest | Install `backend/requirements-dev.txt`; runtime-only requirements omit test tools. |
| Model unavailable offline | Run the inference CLI once with network access; then use `--offline` with the same `MODEL_CACHE_DIR`. |
| Model cannot download | Check network/proxy access to Hugging Face; model-load failure is reported in backend logs and `/health`. |
| Port already in use | Stop the other development instance or change `PORT` and the frontend `BACKEND_URL` together. |
| Activation denied | Run the venv Python by its explicit path; activation is unnecessary. |

### Frontend (a second terminal, from the repository root)

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open the local URL printed by Vite. To verify a production build:

```powershell
npm run build
```

Vite proxies `/health`, `/transcribe`, `/transcriptions`, and `/search` to the
backend, so the React client uses same-origin relative URLs. The
default target is `http://127.0.0.1:5000`; copy `frontend/.env.example` to
`frontend/.env` and set `BACKEND_URL` if the backend port changes. Restart Vite
after changing it. This proxy is for native development only; the frontend
container uses Nginx instead. Broad CORS access is not enabled.

## Full application containers 

See [docs/containers.md](docs/containers.md) for build/start commands, volumes,
permissions, configuration, replacement testing, and all container assumptions.
Install and start Docker with Linux container support and the Compose plugin.
The Linux/x86-64 image has been built and tested. If `docker` is missing from
PATH, reopen the terminal and check your Docker installation as described in
[docs/containers.md](docs/containers.md).

```powershell
# From the repository root, with Docker Engine and the Compose plugin running:
docker compose config
docker compose up -d --build
docker compose logs -f backend frontend
```

The frontend serves React at `http://127.0.0.1:3000` and proxies API requests to
`backend:5000` inside Docker. No frontend `.env` is needed for Compose. The
backend is also published for direct API testing at `http://127.0.0.1:8000` and uses a single
Gunicorn worker with four threads. SQLite/uploads and model cache live in separate
named volumes. The first start downloads Whisper; subsequent starts reuse its
volume. Set `BACKEND_URL=http://127.0.0.1:8000` in `frontend/.env` and restart Vite
to use this backend. The native Python setup remains available on port 5000.

The Docker build installs Python/dependencies inside the image, including CPU-only
PyTorch and Gunicorn. It does not copy the host `.venv`, `.env`, samples, database,
or cache. `requirements-docker.txt` is for the Linux image; keep using
`requirements-dev.txt` for Windows development/testing. The container runs as
UID/GID 10001. Linux execution and write access to both named volumes passed.

Validation passed with Docker Engine 29.8.1, Compose 5.5.1, Python 3.12.14,
CPU PyTorch 2.8.0+cpu, and libsndfile 1.2.2. All three samples plus a duplicate
returned nonempty transcriptions; listing, searches, and invalid/oversized request
checks passed. Forced container replacement preserved all four records and every
audio/model file hash. The replacement became healthy with the retained cache.
`pip check` also passed inside the image. The optional HTTP checks require the
three separately supplied sample MP3s in the repository root, or a `--sample-dir`
argument on the `before` command. Run from `backend/`:

```powershell
.venv/Scripts/python.exe -m scripts.validate_container before
# From repository root: docker compose up -d --no-build --force-recreate backend
# Wait for healthy status, then from backend/:
.venv/Scripts/python.exe -m scripts.validate_container after
```

The validation intentionally retains four tagged records in the Docker data volume.
These checks establish local container operation, not production load capacity or
transcription accuracy. See the container guide for assumptions and full details.

## Architecture and documentation tooling

Read [architecture.pdf](architecture.pdf) for the two-page architecture diagram
and assumptions, or [docs/architecture.md](docs/architecture.md) for the detailed
flow and source mapping. The diagram separates runtime audio flow from startup
model downloads. The Mermaid source is `docs/architecture.mmd`; the exact PDF
drawing source is `docs/build_architecture.py`. Update both when architecture changes.

PDF generation is optional and separate from running the application. To recreate
the documentation environment from an installed Python 3.12, run from the root:

```powershell
py -3.12 -m venv .venv-docs
.venv-docs/Scripts/python.exe -m pip install -r docs/requirements-docs.txt
.venv-docs/Scripts/python.exe docs/build_architecture.py
```

Use a verified full Python executable path instead of `py -3.12` if the launcher
is unavailable, as explained in Local setup. Activation is unnecessary. The script
always writes `architecture.pdf` at the repository root. It needs only ReportLab
4.4.9; no model downloads, backend server, or audio samples are needed.
PDF generation was verified with Python 3.12 and ReportLab 4.4.9. The optional
clean environment commands above were not separately exercised. Documentation
dependencies are separate from application requirements.

For visual verification, render with Poppler (`pdftoppm` on PATH) and inspect both
PNGs after each diagram edit:

```powershell
New-Item -ItemType Directory -Force tmp/pdfs | Out-Null
pdftoppm -scale-to 1400 -png architecture.pdf tmp/pdfs/architecture
```

Both pages were rendered and visually inspected for this delivery. Poppler is
documentation tooling only; it is not a backend dependency. Temporary previews
and `.venv-docs` are excluded from Git. Manual listening remains the outstanding
acceptance task; automated processing checks do not establish recognition accuracy.

## Backend configuration

The app reads `backend/.env`. Process environment variables take precedence over
that file; built-in defaults apply otherwise. Relative paths always resolve
against `backend/`, independent of the current working directory. Empty settings
and invalid numeric limits fail startup with a configuration error.

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_PATH` | `data/transcriptions.sqlite3` | SQLite file |
| `UPLOAD_DIR` | `data/uploads` | Retained recordings |
| `MODEL_CACHE_DIR` | `.cache/huggingface` | Downloaded model cache |
| `MAX_CONTENT_LENGTH` | `26214400` | Flask request limit in bytes (25 MiB) |
| `MAX_AUDIO_DURATION_SECONDS` | `600` | Decoded-audio limit (10 minutes) |
| `HOST` | `127.0.0.1` | Development bind address |
| `PORT` | `5000` | Development port, from 1 through 65535 |

Size and duration limits are configurable. The decoder enforces duration. `HOST` and
`PORT` apply to `python -m app`; a production WSGI server will have its own launch
configuration. Custom runtime paths outside the ignored defaults must also be
excluded from version control.

## API contract and examples

The [API contract](docs/api-contract.md) defines exact field types, validation,
readiness behavior, search semantics, and error codes. All four endpoints are
implemented; response examples below use illustrative transcription text.

| Endpoint | Success | Response shape |
| --- | --- | --- |
| `GET /health` | 200 | `status`, `model_ready`, `database_ready` |
| `POST /transcribe` | 201 | A transcription record directly |
| `GET /transcriptions` | 200 | `{"transcriptions": [...]}` |
| `GET /search?filename=...` | 200 | `{"transcriptions": [...]}` |

Run these PowerShell examples from the repository root with the backend running.
The upload example requires your own `Sample 1.mp3`; recordings are not included:

```powershell
curl.exe http://127.0.0.1:5000/health
curl.exe -F "file=@Sample 1.mp3" http://127.0.0.1:5000/transcribe
curl.exe http://127.0.0.1:5000/transcriptions
curl.exe --get --data-urlencode "filename=sample 1" http://127.0.0.1:5000/search
```

Example ready health response (200):

```json
{"status": "ok", "model_ready": true, "database_ready": true}
```

Example upload response (201; illustrative text, not an actual sample result):

```json
{
  "id": 1,
  "original_filename": "Sample 1.mp3",
  "stored_filename": "Sample_1_f27a51e24b8c.mp3",
  "text": "This is an example transcription.",
  "created_at": "2026-10-01T08:30:00Z"
}
```

Listing and search wrap records in `transcriptions`, ordered newest first with
ID descending to break timestamp ties. Empty results return 200:

```json
{"transcriptions": []}
```

Search is a literal Unicode case-insensitive substring match on the original
filename. Whitespace around the query is trimmed. Blank, missing, or repeated
`filename` parameters return 400; clear search by fetching `/transcriptions`.

Example invalid search response (400):

```json
{"error": {"code": "invalid_query", "message": "Provide one nonempty filename query."}}
```

Every error contains `error.code` and `error.message`. Invalid input returns 400,
oversized requests 413, unsupported media/formats 415, unavailable or busy service
503, and unexpected failures 500. Health failures also report readiness fields.
See the contract for the complete code mapping, including JSON 404/405 responses.

Initial uploads support MP3 only, one file per request. The React batch
flow submits files sequentially. Duplicate uploads create separate records;
clients should not automatically retry an upload after an ambiguous network
failure. Success is returned only after transcription and database commit.

## Persistence and file storage

App startup creates the database parent directory, schema, and upload directory
idempotently. The repository and storage instances are registered under
`app.extensions["transcription_repository"]` and `app.extensions["upload_storage"]`.
Each database operation opens and closes its own connection. Inserts commit before
returning; SQL errors roll back. Listing and search use timestamp/ID descending
ordering, with parameterized queries and Unicode case folding for literal search.

`transcribe_and_store` accepts a binary stream, filename, repository, storage,
and a `transcribe(path)` callback. It saves using exclusive creation and a unique
suffix, calls the callback, then saves the result. Copy, callback, or database
failure removes the new file. Successful files remain alongside committed records.
The original basename is preserved separately from the sanitized stored filename.
The upload route uses `WhisperTranscriber.transcribe` as its callback after HTTP
validation and dependency readiness checks. Successful responses follow database
commit. Unexpected errors return a generic 500 and are logged on the backend;
success logs contain record ID and elapsed time, not audio or transcript content.

SQLite transactions and filesystem operations are not one atomic transaction.
Cleanup covers normal exceptions; an abrupt process/machine failure can leave an
orphan file. Crash recovery/reconciliation is outside this step. Runtime storage
directories are assumed to be backend-controlled, not writable by untrusted users.

## Local audio inference

The pipeline uses SoundFile/libsndfile to verify and decode MP3 content, averages
channels to mono, and resamples to 16 kHz float32 with SciPy. It enforces the
configured duration on both metadata and decoded sample counts. MP3 is the only
accepted input format. The pinned SoundFile wheel includes libsndfile on this
Windows environment; no FFmpeg executable is required. Other platforms must
provide an MP3-capable libsndfile if a bundled wheel is unavailable.

The service loads `openai/whisper-tiny` and its processor from Hugging Face into
`MODEL_CACHE_DIR`, uses CPU float32 inference in evaluation mode with gradients
disabled, and requests transcription with language detection. Recordings over
30 seconds use sequential long-form generation with timestamps and untruncated
features; shorter recordings are padded to the standard model window.
See [Hugging Face's Whisper documentation](https://huggingface.co/docs/transformers/v4.56.2/en/model_doc/whisper)
and [SoundFile documentation](https://python-soundfile.readthedocs.io/).

The app registers a process-local service as `app.extensions["transcriber"]`.
Call `load()` explicitly before transcription; app creation does not download
weights. `ready` stays false after a failed load, and loading can be retried.
Once loaded, the model is reused. A nonblocking lock rejects overlapping decode/
inference requests with `ServiceBusy` and is released even after failure.
The server entry point loads the model and `/health` reports both model and
database readiness. A busy model remains ready, but overlapping uploads receive
503 with `service_busy`. The lock applies per process; use one model worker for
the initial deployment.

From `backend/`, run real inference without starting the HTTP server:

```powershell
.venv/Scripts/python.exe -m app.transcribe_files "../Sample 1.mp3" "../Sample 2.mp3" "../Sample 3.mp3" --output data/sample-transcriptions.json
```

The initial run requires internet access to download model assets. Repeat with
`--offline` to reuse the local snapshot directly without remote lookups. Audio stays local; only model
assets are downloaded. The command prints timing and transcript results and
optionally saves them to the ignored data directory; it does not insert records
into SQLite. Model-generated text can contain recognition errors, especially
with silence or unclear speech; manual accuracy review remains necessary.

### Real inference validation (2026-10-01)

All three samples produced nonempty transcripts on CPU and succeeded again offline.

| Input | Duration | Offline inference time |
| --- | --- | --- |
| Sample 1.mp3 | 13.120 s | 1.51 s |
| Sample 2.mp3 | 11.051 s | 1.20 s |
| Sample 3.mp3 | 12.843 s | 1.24 s |
| Combined samples 1–3 | 37.013 s | 3.28 s |

The combined recording includes the final sample's closing sentence in its output,
confirming generation beyond the first 30 seconds. Wording differs slightly from
individual runs, so this is a coverage check, not an accuracy score. Manual
listening-based accuracy review is still pending. Results are saved locally in
`backend/data/sample-transcriptions.json` and `backend/data/offline-validation.json`.
These files, the derived recording, and model weights are excluded from Git.

Initial model download/load took 153.76 seconds; a subsequent offline load took
7.89 seconds while tests were also running. Timings depend on hardware/cache state.
The validated Hugging Face snapshot was
`169d4a4341b33bc18d8881c4b69c2e104e1cc0af`; future online loads follow the model's
default revision. MP3 decoding used libsndfile 1.2.2.

## Tests and validation

The automated suite contains **exactly three backend unit tests and three
frontend component unit tests**. No model downloads, private recordings, running
server, database, or real upload files are needed for these six tests.

| Side | Test | Checks |
| --- | --- | --- |
| Backend | Successful upload | Route/workflow calls mocked storage, inference, and repository, then returns the committed record with 201. |
| Backend | Duplicate filenames | Filename allocation produces distinct paths and uses exclusive creation; filesystem writes are mocked. |
| Backend | Filename search | Route forwards the query to the mocked repository and returns its matches without invoking inference. |
| Frontend | Batch upload | Sequential submission, per-file results, and continuation after one failure, with mocked HTTP. |
| Frontend | Listing | Stored filenames, transcript text, and timestamps render from mocked HTTP results. |
| Frontend | Search | Filename search filters the display; clearing restores the full list, with mocked HTTP. |

**Backend (PowerShell, from the repository root):**

```powershell
# One-time setup if backend/.venv does not exist:
py -3.12 -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements-dev.txt
# Run exactly three tests:
backend/.venv/Scripts/python.exe -m pytest -q backend/tests
```

See Local setup for alternatives when `py` is unavailable. From `backend/`, the
equivalent command is `.venv/Scripts/python.exe -m pytest -q`. The tests use
`unittest.TestCase` with mocks and are collected by pytest.

**Frontend (from the repository root, using Node.js):**

```powershell
cd frontend
npm ci
npm test
```

Expected result: **3 passed** for each side. The frontend Docker build also runs
its three tests: `docker compose build frontend` from the repository root. To
force an uncached run, use `docker compose build --no-cache frontend`.
`npm run build` checks production compilation separately; it is not a unit test.

Test files and boundaries are mapped in [docs/testing.md](docs/testing.md).
The optional integration scripts below are separate manual validation tools;
they are not collected by the six-test automated suite.

For the optional real-model API check, obtain the three validation recordings
separately and place `Sample 1.mp3`, `Sample 2.mp3`, and `Sample 3.mp3` in the
repository root (ignored by Git), or specify `--sample-dir`. These recordings
are not included in a clone. From `backend/`, after caching the model:

```powershell
.venv/Scripts/python.exe -m scripts.validate_samples
```

This command uses the three repository-root samples, temporary storage, Flask's
test client, and a fresh Python process to verify persistence. It requires cached
weights by default. Use `--sample-dir '../private-samples'` for another folder,
or explicitly pass `--allow-download` for the initial model download. It prints
pass/fail without recording transcripts in version control. This is an integration
smoke test, not a listening-based accuracy assessment or full browser automation.

### Assumptions by step

| Step | Assumptions and limits |
| --- | --- |
| 1. Structure/configuration | Validated Windows/Python 3.12 environment; one local repository; relative runtime paths resolve under `backend/`. |
| 2. API contracts | One file per synchronous request; batch behavior belongs to React; no authentication or pagination for the assignment. |
| 3. Persistence/storage | Small single-instance SQLite workload; backend-controlled storage; exception cleanup is supported, abrupt-crash recovery is not. |
| 4. Audio/inference | MP3 only, local CPU Whisper Tiny, automatic language detection; model assets require an initial download; transcripts need human accuracy review. |
| 5. Flask routes | One inference worker per process; busy requests return 503; Vite proxy is development-only; health is not a guarantee of future write success. |
| 6. React UI | Sequential batches; timestamps displayed in the browser's locale; no automatic POST retries after ambiguous network failures. |
| 7. Testing | Exactly three unit tests per side; backend storage, inference, database, and frontend HTTP dependencies are mocked. Optional integration scripts remain separate; private recordings are excluded from Git. |
| 8. Containerization (validated) | Linux/x86-64 CPU backend, one threaded worker, UID/GID 10001, persistent named volumes; Nginx frontend serves the production React build on port 3000; build, API, permissions, and replacement persistence passed locally. Other architectures and production load remain unverified. |
| 9. Architecture/delivery (complete) | PDF and editable sources reflect the implemented local-inference design; both PDF pages were visually checked. Documentation tooling is optional and separate from application dependencies. Manual accuracy review remains pending. |

Detailed assumptions also appear inside each corresponding step in
`project_guidelines.md`. The supplied assignment begins at section 2; omitted
requirements, if any, could change these assumptions.

Separate real-model validation through Flask's test client passed for all three
samples plus a duplicate upload (four 201 responses), health readiness, listing,
matching/nonmatching searches, and persistence across app recreation. These checks
used temporary storage, so they did not populate the default application database.
The frontend production build also passes with the development proxy configured.

Verified for step 1: Flask app creation, default and relative-path configuration,
file/environment precedence, rejection of invalid settings, dependency consistency
(`pip check`), Git ignore rules, and `npm run build`. The frontend lockfile records
the installed dependency versions. Real audio inference was validated in step 4
as described above; dependency consistency was checked again after installation.

The three sample MP3s used for validation are not distributed with this repository.
The automated test suite needs no private recordings. Their inspected properties were: all are mono at 48 kHz, with durations
13.120 seconds (Sample 1), 11.051 seconds (Sample 2), and 12.843 seconds (Sample 3).
The 25 MiB / 600-second limits accommodate all supplied recordings. Local `.env`
files, runtime data, models, dependencies, and build outputs are also ignored.
