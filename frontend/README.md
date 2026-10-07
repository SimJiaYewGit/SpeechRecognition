# React interface

For the full container setup, run `docker compose up -d --build` from the
repository root and open `http://127.0.0.1:3000`. Docker builds/tests React and
serves static files with Nginx; API calls go to the backend service. No host Node
or Python installation and no frontend `.env` are needed for this path.
See the root README and `docs/containers.md` for readiness and persistence.

For native development, from this directory, install with `npm ci`, then run `npm run dev`.
Start the backend in a second terminal using the root README instructions.
The development proxy targets `http://127.0.0.1:5000` by default.

## User workflow

1. Select one or several MP3 recordings. Empty files and non-MP3 filenames show
   validation errors. The backend checks actual format, size, and duration.
2. Select **Transcribe recordings**. Files run sequentially with queued,
   processing, completed, or failed status. One failure does not stop the batch.
   File selection and submission are disabled while processing to prevent duplicates.
3. Read saved transcriptions, with original filenames and local creation times.
   Successful uploads refresh results automatically. Use **Refresh** to retry
   listing after an ambiguous network failure before uploading the same file again.
4. Search by full or partial filename. **Clear search** restores the full list.
   Uploads refresh the active query; stale requests cannot replace newer results.

The responsive layout stacks on narrow screens. Controls have labels and keyboard
focus indicators; loading, empty, failed, and batch-summary states are visible.
Transcripts are rendered as text, not HTML. Uploads are never retried automatically.

## Tests and build

```powershell
npm test
npm run build
```

`npm run test:watch` runs interactive tests. Exactly three Vitest/React Testing
Library component unit tests mock HTTP: batch upload, listing, and search/clear.
They need no backend or model. The frontend Docker build runs the same tests
before compiling the production bundle. See the root README for setup commands.

The Vite proxy is development-only. The frontend container uses Nginx to route
API paths to Flask. Frontend configuration belongs in `.env` (see `.env.example`).
