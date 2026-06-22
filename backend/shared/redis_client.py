import redis

from backend.shared.config import settings


def get_redis_client() -> redis.Redis:
    # socket_timeout must exceed any blocking command's own timeout (e.g. the
    # worker's BRPOP), otherwise redis-py's client-side read timeout races
    # the server-side blocking timeout and raises spurious TimeoutErrors.
    return redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_timeout=settings.worker_poll_timeout_seconds + 5,
    )
