"""Load local configuration without changing process environment variables."""

import os
from pathlib import Path

from dotenv import dotenv_values

BACKEND_DIR = Path(__file__).resolve().parents[1]


def load_config():
    """Environment variables override backend/.env, which overrides defaults."""
    values = {**dotenv_values(BACKEND_DIR / ".env"), **os.environ}

    def value(name, default):
        raw = values.get(name, default)
        if raw is None or not str(raw).strip():
            raise ValueError(f"{name} must not be empty")
        return str(raw).strip()

    def path(name, default):
        # Anchor paths to the source tree so CLI and WSGI launch directories agree.
        result = Path(value(name, default)).expanduser()
        if not result.is_absolute():
            result = BACKEND_DIR / result
        return str(result.resolve())

    def positive_integer(name, default, maximum=None):
        try:
            result = int(value(name, default))
        except ValueError as error:
            raise ValueError(f"{name} must be a positive integer") from error
        if result <= 0 or (maximum is not None and result > maximum):
            limit = f" between 1 and {maximum}" if maximum else " greater than zero"
            raise ValueError(f"{name} must be{limit}")
        return result

    return {
        "DATABASE_PATH": path("DATABASE_PATH", "data/transcriptions.sqlite3"),
        "UPLOAD_DIR": path("UPLOAD_DIR", "data/uploads"),
        "MODEL_CACHE_DIR": path("MODEL_CACHE_DIR", ".cache/huggingface"),
        "MAX_CONTENT_LENGTH": positive_integer("MAX_CONTENT_LENGTH", 25 * 1024 * 1024),
        "MAX_AUDIO_DURATION_SECONDS": positive_integer("MAX_AUDIO_DURATION_SECONDS", 600),
        "HOST": value("HOST", "127.0.0.1"),
        "PORT": positive_integer("PORT", 5000, maximum=65535),
    }
