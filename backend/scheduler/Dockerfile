FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/__init__.py backend/__init__.py
COPY backend/shared backend/shared
COPY backend/scheduler backend/scheduler

ENV PYTHONPATH=/app

CMD ["python", "-m", "backend.scheduler.main"]
