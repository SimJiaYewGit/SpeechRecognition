# Frontend unit tests

Exactly three React component tests live in `App.test.jsx`: batch upload,
transcription listing, and filename search/clear. HTTP is mocked; no running
backend, model, or private recordings are required.

From `frontend/`, run `npm ci` once, then `npm test`. Expected: `3 passed`.
Use `npm run test:watch` during edits. The frontend Docker build runs the same
three tests before packaging the production bundle.
