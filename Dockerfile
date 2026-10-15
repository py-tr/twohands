# Two Hands web app (+ Evolus integration). Keys come only from the environment at run time (env_file),
# never from the image: .env is excluded by .dockerignore.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TWOHANDS_RATE_FILE=/app/app/state/ratelimit.json

# libglib2.0-0: needed by opencv-python-headless at import time on slim images
RUN apt-get update \
 && apt-get install -y --no-install-recommends libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt requirements-app.txt ./
RUN pip install -r requirements.txt

COPY . .
RUN useradd --create-home --uid 10001 twohands \
 && mkdir -p /app/app/state /app/cache \
 && chown -R twohands:twohands /app/app/state /app/cache
USER twohands

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4).status == 200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
