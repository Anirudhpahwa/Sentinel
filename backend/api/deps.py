from collections.abc import Generator

import redis
from sqlalchemy.orm import Session

from backend.shared.db import SessionLocal
from backend.shared.redis_client import get_redis_client


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# A single long-lived, connection-pooled client, same idiom as the other
# services -- not constructed per-request.
_redis_client = get_redis_client()


def get_redis() -> redis.Redis:
    return _redis_client
