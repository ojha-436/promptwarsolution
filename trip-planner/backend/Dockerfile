# ── Build stage ────────────────────────────────────────────────────────────
FROM python:3.12-slim AS build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app
COPY requirements.txt ./
RUN pip install --upgrade pip \
 && pip install --prefix=/install -r requirements.txt

# ── Runtime stage ──────────────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Create non-root user
RUN groupadd --system app && useradd --system --gid app --uid 1001 app

WORKDIR /app
COPY --from=build /install /usr/local
COPY app /app/app

# Read-only filesystem-friendly: no writable layers needed
USER 1001
EXPOSE 8080

# Cloud Run sends SIGTERM and respects PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 2 --log-config=- --no-access-log"]
