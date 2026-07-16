# Backend deployment image (Railway). Built with the repo root as build
# context (see railway.json) because the backend needs prompts/ — the
# canonical SAGE source of truth and provider configs — which lives outside
# backend/ as a sibling directory. The frontend is deployed separately
# (Vercel) and is not part of this image.
FROM python:3.12-slim

WORKDIR /app

COPY backend/pyproject.toml backend/pyproject.toml
COPY backend/app backend/app
RUN pip install --no-cache-dir ./backend

COPY prompts prompts

ENV SAGE_PROMPTS_ROOT=/app/prompts
WORKDIR /app/backend

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
