# ============================================================================
# Keepwell Backend Multi-Stage Dockerfile (kw-api & kw-worker)
# Build context: repository root (keepwell/)
# ============================================================================

# --- Stage 1: Dependency builder ---
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY services/requirements.txt ./requirements.txt
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt

# --- Stage 2: Runtime ---
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080 \
    SERVICE_ROLE=api

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 kwuser \
    && useradd --uid 10001 --gid 10001 --shell /usr/sbin/nologin --create-home kwuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY services ./services
COPY db ./db
COPY kb ./kb
COPY input/dataset ./input/dataset

RUN chown -R kwuser:kwuser /app

USER kwuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -fsS http://127.0.0.1:${PORT}/healthz || exit 1

ENTRYPOINT ["/bin/sh", "-c"]
CMD ["if [ \"$SERVICE_ROLE\" = \"worker\" ]; then exec uvicorn services.worker.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers; else exec uvicorn services.api.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --ws-ping-interval 20 --ws-ping-timeout 20; fi"]
