"""Manual inference CLI; quote each filename containing spaces."""

import argparse
import json
from pathlib import Path
from time import perf_counter

from .audio import decode_audio
from .config import load_config
from .transcription import get_transcriber


def main():
    parser = argparse.ArgumentParser(description="Validate local Whisper inference on MP3 files")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--offline", action="store_true", help="Use previously cached model assets only")
    parser.add_argument("--output", type=Path, help="Optional local JSON results file")
    args = parser.parse_args()
    config = load_config()
    service = get_transcriber(config["MODEL_CACHE_DIR"], config["MAX_AUDIO_DURATION_SECONDS"])
    started = perf_counter()
    service.load(local_files_only=args.offline)
    print(f"Model ready in {perf_counter() - started:.2f}s", flush=True)
    results = []
    for path in args.files:
        audio = decode_audio(path, config["MAX_AUDIO_DURATION_SECONDS"])
        started = perf_counter()
        text = service.transcribe(path)
        result = {"filename": path.name, "duration_seconds": audio.duration_seconds,
                  "source_sample_rate": audio.source_sample_rate,
                  "source_channels": audio.source_channels,
                  "inference_seconds": round(perf_counter() - started, 2), "text": text}
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
