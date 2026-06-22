FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/__init__.py backend/__init__.py
COPY backend/shared backend/shared
COPY db/migrations db/migrations

ENV PYTHONPATH=/app
WORKDIR /app/db/migrations

CMD ["alembic", "upgrade", "head"]
