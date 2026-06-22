"""Redis list used as a FIFO job queue. The message payload is intentionally
minimal -- just enough to look the execution up in Postgres, which remains
the source of truth for the job's actual content.
"""

import json
import uuid
from typing import Any

import redis

from backend.shared.config import settings


def enqueue_execution(client: redis.Redis, execution_id: uuid.UUID, job_id: uuid.UUID) -> None:
    message = json.dumps({"execution_id": str(execution_id), "job_id": str(job_id)})
    client.lpush(settings.job_queue_key, message)


def dequeue_execution(client: redis.Redis, timeout: int) -> dict[str, Any] | None:
    """Blocking pop with a timeout so the worker loop can periodically wake
    up (e.g. for future shutdown signal checks) instead of blocking forever.
    """
    result = client.brpop(settings.job_queue_key, timeout=timeout)
    if result is None:
        return None
    _, raw_message = result
    return json.loads(raw_message)
