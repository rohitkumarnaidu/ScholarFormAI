FROM python:3.14-slim AS builder
WORKDIR /build
COPY requirements-render.txt requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --prefix=/install -r requirements-render.txt

FROM python:3.14-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY --from=builder /install /usr/local
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY alembic.ini .
COPY alembic/ alembic/
COPY app/ app/
COPY requirements-render.txt requirements.txt .
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health/live')" || exit 1

# Entrypoint script: run migrations before starting the app
COPY --chmod=755 <<'EOF' /app/docker-entrypoint.sh
#!/bin/sh
set -e

# Run Alembic migrations if DB is available
if [ -n "$SUPABASE_DB_URL" ]; then
    echo "Running Alembic migrations..."
    alembic upgrade head || echo "WARNING: Migration failed, continuing anyway"
else
    echo "SUPABASE_DB_URL not set, skipping migrations"
fi

# Start the app
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-1}
EOF

CMD ["/app/docker-entrypoint.sh"]
