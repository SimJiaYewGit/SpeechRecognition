# Testing

## Exact unit-test scope

The project contains exactly **three backend unit tests and three frontend
component unit tests**, as requested. Extra automated test cases were removed;
application behavior was not changed. The six tests do not require a database,
model weights, private audio samples, external HTTP, or a running server.

| Side | File / test | Verified behavior |
| --- | --- | --- |
| Backend | `backend/tests/test_backend.py`: `test_successful_upload_returns_committed_record` | Upload route/workflow calls mocked storage, inference, and repository and returns the record with 201. |
| Backend | `test_duplicate_filenames_allocate_distinct_exclusive_files` | Real filename allocator chooses distinct paths and opens exclusively; UUIDs and disk writes are mocked. |
| Backend | `test_filename_search_passes_query_and_returns_matches` | Search route delegates the query to the mocked repository and returns matches without inference. |
| Frontend | `frontend/src/tests/App.test.jsx`: `renders stored filenames, text, and timestamps` | Listing renders the HTTP fixture. |
| Frontend | `submits a batch sequentially, blocks duplicates, and continues after failure` | Batch submission remains sequential and reports per-file outcomes. |
| Frontend | `searches filenames and clears back to all records` | Search filters displayed results and clear restores the full list. |

## Commands

Create the Python environment and install `backend/requirements-dev.txt` using
the root README. From the repository root:

```powershell
backend/.venv/Scripts/python.exe -m pytest -q backend/tests
```

From `frontend/`, with Node.js installed:

```powershell
npm ci
npm test
```

Expected: `3 passed` for each command. The frontend image build executes the same
three tests and then compiles the production bundle. From the repository root:

```powershell
docker compose build frontend
```

Use `--no-cache` if a fresh execution is needed rather than a cached Docker build
step. Backend tests are not included in its runtime Docker image.

## Assumptions and limits

- Backend tests use real Flask routing and upload orchestration with mocked I/O.
  They do not prove SQLite search semantics, real MP3 decoding, model accuracy,
  crash cleanup, concurrency, or container networking.
- Frontend tests run components in jsdom with mocked fetch. They do not establish
  cross-browser compatibility, exhaustive accessibility, or actual HTTP behavior.
- Multiple assertions within a scenario do not add test cases. There are three
  discovered tests per side; no extra cases are hidden behind markers or filters.
- Manual listening-based transcription accuracy review remains pending.

## Separate integration validation

`backend/scripts/validate_samples.py` and `validate_container.py` are optional,
explicitly invoked integration scripts. They are outside automated test discovery
and do not add unit-test cases. They require separately supplied recordings and
cached model assets (or permitted initial downloads). See the README and
[containers.md](containers.md) for commands and retention behavior.

Earlier integration checks passed for the three recordings, duplicate handling,
filename searches, JSON errors, and persistence. Docker checks also verified
static serving, proxy errors, and recovery after backend replacement. These
historical checks are separate from the current six-test unit suite. They do not
establish word-level accuracy or production capacity.

The architecture PDF was rendered and inspected after updating its test counts.
Comments and docstrings explain responsibilities, mock boundaries, and lifecycle
choices. Optional documentation tooling is described in the README.
