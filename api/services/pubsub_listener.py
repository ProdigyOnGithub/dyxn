import asyncio
import json

from core.redis import redis_client
from api.services.websocket_manager import manager

async def listen_progress():
    """
    Listens to Redis PubSub for 'progress:*' events and broadcasts them
    to the active WebSocket connections.
    """
    pubsub = redis_client.pubsub()
    pubsub.psubscribe("progress:*")

    while True:
        message = pubsub.get_message(ignore_subscribe_messages=True)
        
        if message:
            channel = message["channel"]
            if isinstance(channel, bytes):
                channel = channel.decode()

            document_id = channel.split(":")[1]
            payload = json.loads(message["data"])

            await manager.broadcast(
                document_id,
                payload
            )

        await asyncio.sleep(0.01)
