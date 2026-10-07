"""Small container readiness probe; does not import/load the inference stack."""

import json
import os
import sys
from urllib.error import URLError
from urllib.request import urlopen


def main():
    try:
        port = int(os.environ.get("PORT", "5000"))
        with urlopen(f"http://127.0.0.1:{port}/health", timeout=3) as response:
            body = json.load(response)
            ready = (response.status == 200 and body.get("status") == "ok"
                     and body.get("model_ready") is True and body.get("database_ready") is True)
        return 0 if ready else 1
    except (URLError, OSError, ValueError):
        return 1


if __name__ == "__main__":
    sys.exit(main())
