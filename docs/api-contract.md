# API contract

Status: defined in step 2 and implemented in step 5.
Examples are illustrative, not responses from a running transcription service.
This document is the shared contract for the Flask routes, React client, and tests.

## Common conventions

- Development base URL: `http://127.0.0.1:5000`.
- Paths have no `/api` prefix and no trailing slash.
- Responses use `Content-Type: application/json` and UTF-8 text.
- No authentication or pagination in the initial assignment scope.
- All fields listed below are required and non-null unless explicitly stated.
- Timestamps are UTC ISO 8601 strings ending in `Z`.
- Clients use error codes for decisions and messages for display. Message wording
  may change without changing the contract.
- No absolute storage paths, stack traces, or internal exception messages appear
  in responses. Stored filenames are identifiers, not downloadable URLs.

## Shared transcription record

| Field | JSON type | Meaning |
| --- | --- | --- |
| `id` | integer | Positive database-generated record ID |
| `original_filename` | string | Original basename, with both Windows and POSIX path components removed |
| `stored_filename` | string | Sanitized, unique basename used by backend storage |
| `text` | string | Recognized text; may be empty for valid audio without recognized speech |
| `created_at` | string | UTC timestamp assigned when the successful result is saved |

Example (text is fictional and does not describe the supplied sample):

```json
{
  "id": 1,
  "original_filename": "Sample 1.mp3",
  "stored_filename": "Sample_1_f27a51e24b8c.mp3",
  "text": "This is an example transcription.",
  "created_at": "2026-10-01T08:30:00Z"
}
```

The unique suffix format is an internal detail; clients must not parse it.
Uploading the same filename or bytes again creates a new record. The API has no
deduplication or idempotency key. Do not automatically retry uploads after an
ambiguous connection failure: the first request may already have been saved.

## GET /health

No request parameters or body. Reports service readiness, not queue capacity.
Check database accessibility and model readiness without performing inference.

`200 OK` when both dependencies are ready:

```json
{
  "status": "ok",
  "model_ready": true,
  "database_ready": true
}
```

`503 Service Unavailable` if either dependency is unavailable:

```json
{
  "status": "unavailable",
  "model_ready": false,
  "database_ready": true,
  "error": {
    "code": "service_unavailable",
    "message": "The transcription service is not ready."
  }
}
```

The 503 response retains the common `error` object and adds readiness fields.
A model already processing a recording remains ready; `/health` can return 200
while another upload receives `service_busy`. Listing and search do not require
model readiness and remain available if the database is accessible.

## POST /transcribe

Request: `multipart/form-data`, containing exactly one file part named `file`.
Reject missing files, extra file parts (including repeated `file` fields), empty
basenames, and zero-byte files. Clients should let their HTTP library set the
multipart boundary. No language or inference options are exposed initially.

Initial format contract: MP3 only, with a case-insensitive `.mp3` extension and
decodable MP3 content. The provided MIME type is advisory and is not sufficient
to validate a recording. Other formats require an explicit contract update once
their preprocessing support is verified.

The full HTTP request, including multipart overhead, must fit within
`MAX_CONTENT_LENGTH` (currently 25 MiB). Decoded duration must not exceed
`MAX_AUDIO_DURATION_SECONDS` (currently 600 seconds). Equality with either limit
is allowed. These limits remain provisional until sample inspection.

Processing is synchronous: validate, allocate a unique stored filename, decode,
transcribe, persist, and return. `201 Created` returns the shared record directly
(no wrapper). Return success only after the SQLite transaction commits. On
failure, do not retain a partial record; clean up files created by that request.

Only one inference runs at a time. An overlapping valid request receives
`503 service_busy`; there is no background queue, job ID, or polling endpoint.
The frontend handles batches by sending one request per file sequentially and
displaying each result independently. An individual failure does not cancel the
remaining files.

## GET /transcriptions

No required parameters or body. `200 OK`:

```json
{
  "transcriptions": [
    {
      "id": 1,
      "original_filename": "Sample 1.mp3",
      "stored_filename": "Sample_1_f27a51e24b8c.mp3",
      "text": "This is an example transcription.",
      "created_at": "2026-10-01T08:30:00Z"
    }
  ]
}
```

Returns every saved record, ordered by `created_at DESC, id DESC`. An empty
database returns `{"transcriptions": []}` with 200, never 404.

## GET /search?filename=...

Requires exactly one `filename` query parameter. Trim leading and trailing
whitespace and reject a missing, repeated, or blank value with 400. URL-decode
through the framework once. Search only `original_filename`, including its
extension, not the stored filename or transcript text.

Match a literal case-insensitive substring using Unicode case folding on both
the original filename and query. Do not interpret `%`, `_`, `*`, or backslashes
as wildcards or SQL syntax. For example, `sample 1` matches `Sample 1.mp3`, while
`%` matches only names containing a literal percent sign.

`200 OK` uses the same `transcriptions` wrapper and ordering as the listing
endpoint. No matches return `{"transcriptions": []}`. Clearing the frontend
search should call `/transcriptions`, rather than submit a blank query.

## Error contract

All non-success responses use this object, including framework-generated 404
and 405 errors. The readiness response additionally includes the fields shown
above.

```json
{
  "error": {
    "code": "missing_file",
    "message": "Upload one audio file using the file field."
  }
}
```

| HTTP status | Code | Condition |
| --- | --- | --- |
| 400 | `invalid_request` | Malformed multipart request or invalid file-part count/name |
| 400 | `missing_file` | No uploaded file part |
| 400 | `invalid_filename` | Missing, blank, or unusable basename |
| 400 | `invalid_audio` | Zero bytes, corrupt/undecodable MP3, or no decoded samples |
| 400 | `audio_too_long` | Decoded duration exceeds the configured limit |
| 400 | `invalid_query` | Missing, repeated, or whitespace-only filename query |
| 404 | `not_found` | Unknown route |
| 405 | `method_not_allowed` | Unsupported method on an existing route; preserve the `Allow` header |
| 413 | `payload_too_large` | Full request exceeds configured byte limit |
| 415 | `unsupported_media_type` | Upload request is not multipart form data |
| 415 | `unsupported_audio_format` | Unsupported filename extension or identified non-MP3 audio content |
| 503 | `service_unavailable` | Required model/database dependency is not ready or accessible |
| 503 | `service_busy` | Inference slot is occupied |
| 500 | `internal_error` | Unexpected processing/persistence failure |

Use a generic message for 500, for example `An unexpected error occurred.` Log
diagnostics server-side without exposing them in the response. Map known
dependency readiness failures to 503; unexpected exceptions remain 500.

Validation order for uploads: enforce request-size limits when the body is read,
validate media type and multipart structure, validate filename and empty content,
check supported extension, check service availability/capacity, then decode and
validate duration before inference. A client should fix the reported error and
resubmit; requests with multiple problems need not return all errors at once.

## Implementation handoff

- Step 3 provides record persistence, literal Unicode-aware filename search,
  stable ordering, and unique file storage.
- Step 4 supplies model readiness, decoding, duration validation, and inference.
- Step 5 wires these contracts into Flask and installs JSON error handlers.
- Step 6 consumes these shapes in React; step 7 verifies behavior with tests.

Routes and JSON error handlers are implemented. Backend tests cover the contract
with temporary SQLite storage and mocked inference; real cached-model uploads
are also checked separately. Examples above remain illustrative.
