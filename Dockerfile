# Single-service image: builds the frontend, then serves it from the same
# FastAPI app as the API (one container, one domain, no CORS, no second
# hosting platform). Built with the repo root as context because the
# backend needs the sibling prompts/ directory — the canonical SAGE source
# of truth and provider configs. Listens on $PORT (falls back to 8000),
# which is the standard contract for Google Cloud Run as well as Railway —
# this image is unchanged between the two.

FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

COPY backend/pyproject.toml backend/pyproject.toml
COPY backend/app backend/app
RUN pip install --no-cache-dir ./backend

COPY prompts prompts
COPY --from=frontend-build /frontend/dist /app/static

ENV SAGE_PROMPTS_ROOT=/app/prompts
ENV SAGE_STATIC_ROOT=/app/static
# Sane defaults for a platform with no attached persistent volume (e.g. Cloud
# Run) so the app runs with zero required storage env vars. /tmp is writable
# on every target platform; a deployment with real persistent storage (e.g.
# a Railway volume) overrides both at runtime.
ENV SAGE_DB_PATH=/tmp/sage.db
ENV SAGE_ARTEFACT_ROOT=/tmp/artefacts
WORKDIR /app/backend

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
