"""Exclusive upload creation and ownership of files until database commit."""

from pathlib import Path
import shutil
from uuid import uuid4

from werkzeug.utils import secure_filename


class InvalidFilename(ValueError):
    """The supplied filename has no usable basename."""


def original_basename(filename):
    if not isinstance(filename, str):
        raise InvalidFilename("Provide a filename")
    name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    if not name.strip() or name in {".", ".."} or any(ord(c) < 32 for c in name):
        raise InvalidFilename("Provide a usable filename")
    return name


class UploadStorage:
    def __init__(self, upload_dir):
        self.directory = Path(upload_dir).resolve()

    def initialize(self):
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(self, stream, filename):
        """Copy a binary stream, cleaning partial files on read/write failure."""
        original = original_basename(filename)
        # Prefix also avoids reserved Windows device names. Truncation bounds
        # filename length; the original Unicode basename remains in the database.
        safe = secure_filename(original)
        suffix = Path(safe).suffix[:16]
        stem = Path(safe).stem[:80] or "audio"
        for _ in range(10):
            path = self.directory / f"audio_{stem}_{uuid4().hex}{suffix}"
            try:
                output = path.open("xb")
            except FileExistsError:
                continue
            try:
                with output:
                    shutil.copyfileobj(stream, output)
            except BaseException:
                path.unlink(missing_ok=True)
                raise
            return original, path
        raise FileExistsError("Unable to allocate a unique upload filename")


def transcribe_and_store(stream, filename, *, storage, repository, transcribe):
    """Save, transcribe, and commit one upload; remove the file on failure.

    The callback must return text or raise. Keep its file only after insert has
    committed. Routes handle HTTP validation; the transcriber owns model capacity.
    """
    original, path = storage.save(stream, filename)
    try:
        text = transcribe(path)
        record = repository.insert(original, path.name, text)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return record
