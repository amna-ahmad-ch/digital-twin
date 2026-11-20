# Build the Vite UI, then run the FastAPI app with the project knowledge files.
FROM node:22-alpine AS frontend
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/
WORKDIR /srv
COPY backend/pyproject.toml backend/uv.lock /srv/backend/
WORKDIR /srv/backend
RUN uv sync --frozen --no-dev
COPY backend/ /srv/backend/
COPY knowledge/ /srv/knowledge/
COPY --from=frontend /src/frontend/dist /srv/frontend/dist
ENV PATH="/srv/backend/.venv/bin:$PATH"
# Cloud Run sets PORT (8080). Fly and local Docker leave it unset or set 8000.
ENV PORT=8000
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn app.main:app --app-dir /srv/backend --host 0.0.0.0 --port ${PORT}"]
