"""Exactly three backend unit tests; no database, model, or disk writes."""

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call, mock_open, patch

from flask import Flask

from app.routes import api, register_error_handlers
from app.storage import UploadStorage


class BackendUnitTests(unittest.TestCase):
    def setUp(self):
        # Register the real routes without the factory's database/model setup.
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, MAX_CONTENT_LENGTH=26214400)
        self.repo = Mock()
        self.repo.ready.return_value = True
        self.storage = Mock()
        self.service = SimpleNamespace(ready=True, transcribe=Mock(return_value="Recognized text"))
        self.app.extensions.update(transcription_repository=self.repo,
                                   upload_storage=self.storage, transcriber=self.service)
        self.app.register_blueprint(api)
        register_error_handlers(self.app)
        self.client = self.app.test_client()

    def test_successful_upload_returns_committed_record(self):
        path = Path("uploads/audio_sample_unique.mp3")
        record = {"id": 1, "original_filename": "sample.mp3",
                  "stored_filename": path.name, "text": "Recognized text",
                  "created_at": "2026-10-01T08:30:00Z"}
        self.storage.save.return_value = ("sample.mp3", path)
        self.repo.insert.return_value = record
        response = self.client.post("/transcribe", data={
            "file": (BytesIO(b"mock audio"), "sample.mp3"),
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json, record)
        self.storage.save.assert_called_once()
        self.assertEqual(self.storage.save.call_args.args[1], "sample.mp3")
        self.service.transcribe.assert_called_once_with(path)
        self.repo.insert.assert_called_once_with("sample.mp3", path.name, "Recognized text")

    def test_duplicate_filenames_allocate_distinct_exclusive_files(self):
        storage = UploadStorage("uploads")
        # Mock filesystem writes and UUIDs so uniqueness is deterministic and
        # this test exercises the filename allocator without touching the disk.
        opened = mock_open()
        with patch("app.storage.uuid4", side_effect=[SimpleNamespace(hex="a" * 32),
                                                     SimpleNamespace(hex="b" * 32)]), \
                patch("app.storage.Path.open", opened):
            original1, first = storage.save(BytesIO(b"first"), "sample.mp3")
            original2, second = storage.save(BytesIO(b"second"), "sample.mp3")
        self.assertEqual((original1, original2), ("sample.mp3", "sample.mp3"))
        self.assertNotEqual(first.name, second.name)
        self.assertEqual(first.parent, storage.directory)
        self.assertEqual(second.parent, storage.directory)
        self.assertEqual(opened.call_args_list, [call("xb"), call("xb")])
        opened().write.assert_has_calls([call(b"first"), call(b"second")])

    def test_filename_search_passes_query_and_returns_matches(self):
        matches = [{"id": 1, "original_filename": "meeting.mp3",
                    "stored_filename": "audio_meeting_unique.mp3", "text": "Meeting notes",
                    "created_at": "2026-10-01T08:30:00Z"}]
        self.repo.search.return_value = matches
        response = self.client.get("/search", query_string={"filename": " meeting "})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"transcriptions": matches})
        # Query normalization belongs to the repository; the route delegates it.
        self.repo.search.assert_called_once_with(" meeting ")
        self.service.transcribe.assert_not_called()
