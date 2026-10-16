FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY pyproject.toml README.md ./
COPY backend ./backend
COPY alembic.ini ./
COPY alembic ./alembic
RUN pip install --no-cache-dir .

EXPOSE 8080
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT:-8080}"]

