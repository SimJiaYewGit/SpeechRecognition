"""Repeatable real-model API smoke check using disposable storage.

Run from backend/: python -m scripts.validate_samples
The default requires previously cached model assets and never downloads them.
"""

import argparse
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from app import create_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample-dir", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--allow-download", action="store_true")
    args = parser.parse_args()
    paths = [args.sample_dir / f"Sample {number}.mp3" for number in (1, 2, 3)]
    for path in paths:
        if not path.is_file():
            parser.error(f"Missing sample: {path}")

    # Keep smoke-test records out of the user's application database and uploads.
    with TemporaryDirectory() as directory:
        root = Path(directory)
        config = {"TESTING": True, "DATABASE_PATH": str(root / "validation.sqlite3"),
                  "UPLOAD_DIR": str(root / "uploads")}
        app = create_app(config)
        app.extensions["transcriber"].load(local_files_only=not args.allow_download)
        client = app.test_client()
        assert client.get("/health").status_code == 200
        records = []
        for path in [*paths, paths[0]]:
            with path.open("rb") as audio:
                response = client.post("/transcribe", data={"file": (audio, path.name)})
            assert response.status_code == 201, response.json
            assert response.json["text"].strip(), f"Empty transcript: {path.name}"
            records.append(response.json)
        assert len({record["stored_filename"] for record in records}) == 4
        assert len(client.get("/transcriptions").json["transcriptions"]) == 4
        for query in ("Sample 1.mp3", "sample 1"):
            assert len(client.get("/search", query_string={"filename": query}).json["transcriptions"]) == 2
        assert client.get("/search?filename=nonexistent").json == {"transcriptions": []}

        # A separate interpreter verifies disk persistence beyond app recreation.
        check = (
            "import sys; from app import create_app; "
            "app=create_app({'DATABASE_PATH':sys.argv[1], 'UPLOAD_DIR':sys.argv[2]}); "
            "assert len(app.test_client().get('/transcriptions').json['transcriptions']) == 4"
        )
        subprocess.run([sys.executable, "-c", check, config["DATABASE_PATH"], config["UPLOAD_DIR"]],
                       cwd=Path(__file__).resolve().parents[1], check=True)
    print("PASS: health, three real samples, duplicate protection, filename search, and persistence in a fresh process.")
    print("Temporary records removed. Manual listening-based accuracy review remains separate.")


if __name__ == "__main__":
    main()
