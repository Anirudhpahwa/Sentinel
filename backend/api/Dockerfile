FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/__init__.py backend/__init__.py
COPY backend/shared backend/shared
COPY backend/metrics backend/metrics
COPY backend/api backend/api

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
