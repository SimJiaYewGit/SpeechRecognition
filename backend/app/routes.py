"""HTTP contract, validation, and error responses."""

from pathlib import Path
from time import perf_counter

from flask import Blueprint, current_app, jsonify, request
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from .audio import AudioError, UnsupportedAudioFormat
from .storage import InvalidFilename, original_basename, transcribe_and_store
from .transcription import ServiceBusy, ServiceUnavailable

api = Blueprint("api", __name__)


class APIError(Exception):
    def __init__(self, code, message, status=400):
        self.code, self.message, self.status = code, message, status


def repository():
    repo = current_app.extensions["transcription_repository"]
    if not repo.ready():
        raise ServiceUnavailable("The database is unavailable.")
    return repo


@api.get("/health")
def health():
    model_ready = current_app.extensions["transcriber"].ready
    database_ready = current_app.extensions["transcription_repository"].ready()
    ready = model_ready and database_ready
    result = {"status": "ok" if ready else "unavailable", "model_ready": model_ready,
              "database_ready": database_ready}
    if not ready:
        result["error"] = {"code": "service_unavailable", "message": "The transcription service is not ready."}
    return jsonify(result), 200 if ready else 503


@api.get("/transcriptions")
def list_transcriptions():
    return jsonify(transcriptions=repository().list_all())


@api.get("/search")
def search():
    values = request.args.getlist("filename")
    if len(values) != 1 or not values[0].strip():
        raise APIError("invalid_query", "Provide one nonempty filename query.")
    return jsonify(transcriptions=repository().search(values[0]))


@api.post("/transcribe")
def transcribe():
    """Validate one multipart upload before invoking storage and local inference."""
    if request.content_length is not None and request.content_length > current_app.config["MAX_CONTENT_LENGTH"]:
        raise RequestEntityTooLarge()
    if request.mimetype != "multipart/form-data":
        raise APIError("unsupported_media_type", "Use multipart form data for audio uploads.", 415)
    try:
        files = list(request.files.items(multi=True))
    except ValueError as error:
        raise APIError("invalid_request", "Malformed multipart request.") from error
    if not files:
        raise APIError("missing_file", "Upload one audio file using the file field.")
    if len(files) != 1 or files[0][0] != "file":
        raise APIError("invalid_request", "Upload exactly one file using the file field.")
    upload = files[0][1]
    name = original_basename(upload.filename)
    # Flask spools uploads into a seekable stream. Rewind after the empty-file probe.
    if not upload.stream.read(1):
        raise AudioError("The recording is empty.")
    upload.stream.seek(0)
    if Path(name).suffix.lower() != ".mp3":
        raise UnsupportedAudioFormat("Only MP3 recordings are supported.")
    repo = repository()
    service = current_app.extensions["transcriber"]
    if not service.ready:
        raise ServiceUnavailable("The transcription model is not ready.")
    started = perf_counter()
    record = transcribe_and_store(upload.stream, name,
                                  storage=current_app.extensions["upload_storage"],
                                  repository=repo, transcribe=service.transcribe)
    current_app.logger.info("Transcription saved: id=%s elapsed_seconds=%.2f", record["id"], perf_counter() - started)
    return jsonify(record), 201


def register_error_handlers(app):
    """Apply the same JSON envelope to domain, framework, and unexpected errors."""
    def error_response(code, message, status):
        return jsonify(error={"code": code, "message": message}), status

    @app.errorhandler(APIError)
    def api_error(error):
        return error_response(error.code, error.message, error.status)

    @app.errorhandler(InvalidFilename)
    def filename_error(error):
        return error_response("invalid_filename", str(error), 400)

    @app.errorhandler(AudioError)
    def audio_error(error):
        return error_response(error.code, str(error), 415 if isinstance(error, UnsupportedAudioFormat) else 400)

    @app.errorhandler(ServiceBusy)
    @app.errorhandler(ServiceUnavailable)
    def service_error(error):
        return error_response(error.code, str(error), 503)

    @app.errorhandler(HTTPException)
    def http_error(error):
        codes = {400: "invalid_request", 404: "not_found", 405: "method_not_allowed", 413: "payload_too_large"}
        response = error.get_response()  # Preserve headers such as Allow.
        response.data = app.json.dumps({"error": {"code": codes.get(error.code, "http_error"),
                                                   "message": error.description}})
        response.content_type = "application/json"
        return response

    @app.errorhandler(Exception)
    def unexpected_error(error):
        app.logger.exception("Unexpected API failure")
        return error_response("internal_error", "An unexpected error occurred.", 500)
