FROM node:22-alpine AS frontend-builder

WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

COPY pyproject.toml README.md ./
COPY backend ./backend
COPY --from=frontend-builder /frontend/dist ./frontend/dist
COPY alembic.ini ./
COPY alembic ./alembic
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT:-8000}"]

