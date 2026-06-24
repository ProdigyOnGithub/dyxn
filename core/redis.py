from redis import Redis
from core.config import config

redis_client = Redis(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    decode_responses=True
)