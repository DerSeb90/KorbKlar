ARG PYTHON_BASE=python:3.13-slim-bookworm@sha256:c45a22ea000adfd9cda29364bbe7edd23001ce5cc2ad15857cfbf7766943b9ca

FROM ${PYTHON_BASE} AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
RUN python -m venv /opt/venv
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN /opt/venv/bin/pip install --upgrade "pip>=26.2" "setuptools>=78.1.1" wheel \
    && /opt/venv/bin/pip install . \
    && /opt/venv/bin/pip uninstall -y pip setuptools wheel \
    && find /opt/venv -type d -name __pycache__ -prune -exec rm -r {} +

FROM ${PYTHON_BASE} AS runtime-rootfs
ARG PYTHON_BASE
RUN apt-get update \
    && apt-get install -y --no-install-recommends chromium ca-certificates curl dumb-init tzdata \
    && python -m pip uninstall -y pip setuptools wheel \
    && rm -rf /root/.cache /var/lib/apt/lists/* /usr/local/lib/python3.13/ensurepip
COPY --from=builder /opt/venv /opt/venv
RUN useradd --system --uid 10001 --create-home --home-dir /home/korbklar korbklar \
    && mkdir -p /data /app \
    && chown -R korbklar:korbklar /data /app

FROM scratch AS final
ARG PYTHON_BASE
COPY --from=runtime-rootfs / /
LABEL org.opencontainers.image.source="https://github.com/lesecuritae/KorbKlar" \
      org.opencontainers.image.version="0.0.3" \
      org.opencontainers.image.base.name="${PYTHON_BASE}"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    SUPERMARKT_DATA_DIR=/data \
    SUPERMARKT_CACHE_DB=/data/supermarkt-cache.sqlite3 \
    SUPERMARKT_SIGNING_SECRET_FILE=/data/.signing-secret \
    SUPERMARKT_IMAGE_CACHE_DIR=/data/supermarkt-images \
    SUPERMARKT_KAUFLAND_CACHE_DIR=/data/kaufland \
    SUPERMARKT_REWE_CACHE_DIR=/data/rewe
WORKDIR /app
USER 10001
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=12 CMD ["curl", "--fail", "--silent", "http://127.0.0.1:8000/health"]
ENTRYPOINT ["dumb-init", "--"]
# --no-proxy-headers is required, not cosmetic. With uvicorn's default
# proxy handling any caller from an allowed peer can rewrite its own
# source address through X-Forwarded-For, which would defeat
# SUPERMARKT_TRUSTED_NETWORKS. KorbKlar evaluates the header itself and
# only for peers listed in SUPERMARKT_TRUSTED_PROXIES.
CMD ["uvicorn", "supermarkt.asgi:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
