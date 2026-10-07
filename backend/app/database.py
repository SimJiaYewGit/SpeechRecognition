"""SQLite persistence independent of Flask and audio inference."""

from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


class TranscriptionRepository:
    def __init__(self, database_path):
        self.path = Path(database_path)

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.create_function("casefold", 1, str.casefold, deterministic=True)
        return connection

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection, connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS transcriptions (
                    id INTEGER PRIMARY KEY,
                    original_filename TEXT NOT NULL,
                    stored_filename TEXT NOT NULL UNIQUE,
                    text TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS transcriptions_created
                ON transcriptions (created_at DESC, id DESC)
            """)

    def ready(self):
        """Check the existing schema without creating a missing database."""
        try:
            with closing(sqlite3.connect(self.path.resolve().as_uri() + "?mode=rw", uri=True, timeout=1)) as connection:
                connection.execute("SELECT id, original_filename, stored_filename, text, created_at FROM transcriptions LIMIT 0")
            return True
        except (sqlite3.Error, OSError):
            return False

    def insert(self, original_filename, stored_filename, text):
        """Insert one completed result and return its record only after commit."""
        if not isinstance(text, str):
            raise TypeError("Transcription text must be a string")
        record = {
            "original_filename": original_filename,
            "stored_filename": stored_filename,
            "text": text,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"),
        }
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute("""
                INSERT INTO transcriptions
                    (original_filename, stored_filename, text, created_at)
                VALUES (:original_filename, :stored_filename, :text, :created_at)
            """, record)
            record["id"] = cursor.lastrowid
        # The transaction has committed and the connection has closed here.
        return record

    def list_all(self):
        """Return newest records first; ID makes equal-timestamp ordering stable."""
        with closing(self._connect()) as connection:
            return [dict(row) for row in connection.execute(
                "SELECT * FROM transcriptions ORDER BY created_at DESC, id DESC"
            )]

    def search(self, filename):
        """Match literal Unicode substrings; SQL LIKE would treat % and _ as wildcards."""
        query = filename.strip()
        if not query:
            raise ValueError("Provide a nonempty filename query")
        with closing(self._connect()) as connection:
            return [dict(row) for row in connection.execute("""
                SELECT * FROM transcriptions
                WHERE instr(casefold(original_filename), ?) > 0
                ORDER BY created_at DESC, id DESC
            """, (query.casefold(),))]
