from redis import Redis

from core.config import config

redis_client = Redis(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    decode_responses=True,
    socket_connect_timeout=config.REDIS_SOCKET_CONNECT_TIMEOUT,
    socket_timeout=config.REDIS_SOCKET_TIMEOUT,
    health_check_interval=30,
)
