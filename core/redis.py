from redis import Redis
from core.config import config

redis_client = Redis(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    decode_responses=True,
    socket_timeout=None,
    socket_connect_timeout=5,
)

print(redis_client.ping())