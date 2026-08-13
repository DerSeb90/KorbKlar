FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SUPERMARKT_DATA_DIR=/data \
    SUPERMARKT_CACHE_DB=/data/supermarkt-cache.sqlite3 \
    SUPERMARKT_SIGNING_SECRET_FILE=/data/.signing-secret \
    SUPERMARKT_IMAGE_CACHE_DIR=/data/supermarkt-images \
    SUPERMARKT_KAUFLAND_CACHE_DIR=/data/kaufland \
    SUPERMARKT_REWE_CACHE_DIR=/data/rewe

RUN apt-get update \
    && apt-get install -y --no-install-recommends chromium ca-certificates curl dumb-init \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir . \
    && useradd --system --uid 10001 --create-home --home-dir /home/korbklar korbklar \
    && mkdir -p /data \
    && chown -R korbklar:korbklar /data

USER korbklar
VOLUME ["/data"]
EXPOSE 8000

ENTRYPOINT ["dumb-init", "--"]
CMD ["uvicorn", "supermarkt.asgi:app", "--host", "0.0.0.0", "--port", "8000"]
