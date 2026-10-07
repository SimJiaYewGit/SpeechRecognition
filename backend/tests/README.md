# Backend unit tests

Exactly three tests live in `test_backend.py`: successful upload, unique filenames
for duplicate uploads, and filename-search delegation/response handling.
Storage, model inference, repository operations, and filesystem writes are mocked.
No SQLite database, actual audio, model downloads, or running backend is required.

Install `backend/requirements-dev.txt` into the project environment as documented
in the root README. From `backend/`, run:

```powershell
.venv/Scripts/python.exe -m pytest -q
```

Expected: `3 passed`. Standard-library discovery also works with
`.venv/Scripts/python.exe -m unittest discover -s tests -v`.
Optional real-model HTTP/persistence scripts under `scripts/` are separate
integration validation tools, not unit tests.
