"""Flask application factory. Importing this package performs no inference or I/O."""

import sqlite3

from flask import Flask, Request

from .config import load_config
from .database import TranscriptionRepository
from .routes import api, register_error_handlers
from .storage import UploadStorage
from .transcription import ServiceUnavailable, get_transcriber


class StrictMultipartRequest(Request):
    def make_form_data_parser(self):
        parser = super().make_form_data_parser()
        parser.silent = False
        return parser


def create_app(config_overrides=None, *, load_model=False):
    """Initialize storage/routes, optionally loading the process-local model.

    Tests leave load_model false and replace the service with a fake. Server
    entry points opt in; a model failure keeps read-only routes available.
    """
    app = Flask(__name__, static_folder=None)
    app.request_class = StrictMultipartRequest
    app.config.from_mapping(load_config())
    if config_overrides is not None:
        app.config.update(config_overrides)
    repository = TranscriptionRepository(app.config["DATABASE_PATH"])
    storage = UploadStorage(app.config["UPLOAD_DIR"])
    try:
        repository.initialize()
    except (sqlite3.Error, OSError):
        app.logger.exception("Database initialization failed; service will report unavailable")
    storage.initialize()
    app.extensions["transcription_repository"] = repository
    app.extensions["upload_storage"] = storage
    # Ordinary app factories/tests stay offline; serving entry points opt in.
    app.extensions["transcriber"] = get_transcriber(
        app.config["MODEL_CACHE_DIR"], app.config["MAX_AUDIO_DURATION_SECONDS"]
    )
    app.register_blueprint(api)
    register_error_handlers(app)
    if load_model:
        service = app.extensions["transcriber"]
        try:
            try:
                service.load(local_files_only=True)
            except ServiceUnavailable:
                service.load()
            app.logger.info("Whisper model ready on CPU")
        except ServiceUnavailable:
            app.logger.exception("Model initialization failed; service will report unavailable")
    return app
