"""Development entry point: run `python -m app` from backend/."""

import logging

from . import create_app

logging.basicConfig(level=logging.INFO)
app = create_app(load_model=True)

if __name__ == "__main__":
    app.run(host=app.config["HOST"], port=app.config["PORT"], debug=False)
