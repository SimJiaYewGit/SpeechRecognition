"""Validate a running container over HTTP before/after replacement.

From backend/: python -m scripts.validate_container before
Then replace the Compose container and run the same command with 'after'.
Records are intentionally retained to verify named-volume persistence.
"""

import argparse
import json
from pathlib import Path
from uuid import uuid4

import requests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["before", "after"])
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--state", type=Path, default=Path("data/container-validation.json"))
    parser.add_argument("--sample-dir", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    base = args.url.rstrip("/")
    health = requests.get(base + "/health", timeout=10)
    assert health.status_code == 200, health.text
    assert health.json()["model_ready"] and health.json()["database_ready"]

    if args.phase == "before":
        tag = "container-check-" + uuid4().hex[:12]
        records = []
        for number in (1, 2, 3, 1):
            path = args.sample_dir / f"Sample {number}.mp3"
            with path.open("rb") as audio:
                response = requests.post(base + "/transcribe", files={
                    "file": (f"{tag}-Sample {number}.mp3", audio, "audio/mpeg")
                }, timeout=600)
            assert response.status_code == 201, response.text
            record = response.json()
            assert record["text"].strip()
            records.append(record)
            print(f"PASS: sample {number}, saved ID {record['id']}", flush=True)
        assert len({record["stored_filename"] for record in records}) == 4
        for query in (tag + "-sample 1", tag + "-Sample 1.mp3"):
            response = requests.get(base + "/search", params={"filename": query}, timeout=10)
            assert response.status_code == 200 and len(response.json()["transcriptions"]) == 2
        assert requests.get(base + "/search", params={"filename": tag + "-missing"}, timeout=10).json() == {"transcriptions": []}

        # Exercise actual HTTP parsing and decoder failures without changing settings.
        invalid = [
            (requests.post(base + "/transcribe", files={"other": ("x.mp3", b"x")}, timeout=10), 400, "invalid_request"),
            (requests.post(base + "/transcribe", files={"file": ("x.mp3", b"")}, timeout=10), 400, "invalid_audio"),
            (requests.post(base + "/transcribe", files={"file": ("x.wav", b"x")}, timeout=10), 415, "unsupported_audio_format"),
            (requests.post(base + "/transcribe", files={"file": ("x.mp3", b"not audio")}, timeout=10), 400, "invalid_audio"),
            (requests.post(base + "/transcribe", data=b"x" * (26214400 + 1), timeout=30), 413, "payload_too_large"),
        ]
        for response, status, code in invalid:
            assert response.status_code == status, (response.status_code, response.text)
            assert response.json()["error"]["code"] == code
        args.state.parent.mkdir(parents=True, exist_ok=True)
        args.state.write_text(json.dumps({"tag": tag, "records": records}, indent=2), encoding="utf-8")
        print("PASS: duplicate filenames, full/partial/no-match search, and upload errors.")
    else:
        records = json.loads(args.state.read_text(encoding="utf-8"))["records"]

    response = requests.get(base + "/transcriptions", timeout=10)
    assert response.status_code == 200
    saved = {row["id"]: row for row in response.json()["transcriptions"]}
    assert all(saved.get(row["id"]) == row for row in records)
    print(f"PASS: {args.phase} replacement, all four records present and unchanged.")


if __name__ == "__main__":
    main()
