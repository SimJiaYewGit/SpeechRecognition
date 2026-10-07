FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_PATH=/data/transcriptions.sqlite3 \
    UPLOAD_DIR=/data/uploads \
    MODEL_CACHE_DIR=/models \
    PORT=5000

WORKDIR /app

# libsndfile provides decoding when a wheel does not bundle it; libgomp is
# needed by CPU numerical libraries. No FFmpeg executable is required.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libsndfile1 libgomp1 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-docker.txt ./
# Install CPU PyTorch first so normal requirements do not pull Linux CUDA wheels.
RUN python -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu \
    && python -m pip install -r requirements-docker.txt \
    && python -m pip check

RUN groupadd --gid 10001 speech \
    && useradd --uid 10001 --gid speech --create-home speech \
    && mkdir -p /data/uploads /models \
    && touch /data/.keep /models/.keep \
    && chown -R speech:speech /data /models

COPY app/ ./app/
COPY gunicorn.conf.py healthcheck.py ./
USER 10001:10001

EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=5s --start-period=600s --retries=3 \
    CMD ["python", "healthcheck.py"]

# The app factory loads cached weights first and downloads only when needed.
# No preload: the model is created inside the single worker process.
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:create_app(load_model=True)"]
