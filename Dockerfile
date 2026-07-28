FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY requirements-docker.txt .
RUN python -m pip install --upgrade pip && \
    python -m pip install --prefix=/install -r requirements-docker.txt

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MALLOC_ARENA_MAX=2 \
    CHRONOS_EMBED_ENGINE=1 \
    HOME=/app \
    PATH=/usr/local/bin:$PATH

WORKDIR /app
RUN addgroup --system chronos && adduser --system --ingroup chronos chronos
COPY --from=builder /install /usr/local
COPY --chown=chronos:chronos . .
RUN mkdir -p /app/.streamlit /app/logs && \
    chmod +x /app/scripts/start.sh && \
    chown -R chronos:chronos /app

USER chronos
EXPOSE 8501
CMD ["/app/scripts/start.sh"]
