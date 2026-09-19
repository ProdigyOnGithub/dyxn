import json
import time
from typing import Any, Callable, Dict

from core.redis import redis_client


class BaseWorker:
    def __init__(self, group_name: str, consumer_name: str, stream_name: str):
        self.group_name = group_name
        self.consumer_name = consumer_name
        self.stream_name = stream_name
        try:
            redis_client.xgroup_create(self.stream_name, self.group_name, id="0", mkstream=True)
        except Exception:
            pass  # group already exists

    def run(self, process_func: Callable[[Dict[str, Any]], None]):
        print(f"Starting {self.consumer_name} listening to {self.stream_name}...")
        while True:
            messages = redis_client.xreadgroup(
                self.group_name,
                self.consumer_name,
                {self.stream_name: ">"},
                count=1,
                block=0,
            )
            if not messages:
                time.sleep(1)
                continue

            _, entries = messages[0]
            for msg_id, data in entries:
                try:
                    process_func(json.loads(data["data"]))
                    redis_client.xack(self.stream_name, self.group_name, msg_id)
                except Exception as e:
                    print(f"Error processing message {msg_id}: {e}")

    def run_batch(self, process_batch_func: Callable[[list], None], batch_size: int = 32):
        print(f"Starting {self.consumer_name} listening to {self.stream_name} (Batched)...")
        while True:
            # block=100 means wait up to 0.1 seconds to fill the batch
            messages = redis_client.xreadgroup(
                self.group_name,
                self.consumer_name,
                {self.stream_name: ">"},
                count=batch_size,
                block=100, 
            )
            
            if not messages:
                time.sleep(0.01) # Small sleep if queue is completely empty and block returned immediately
                continue

            _, entries = messages[0]
            if not entries:
                continue

            msg_ids = []
            payloads = []
            
            for msg_id, data in entries:
                msg_ids.append(msg_id)
                payloads.append(json.loads(data["data"]))
                
            try:
                # Process the whole batch at once
                process_batch_func(payloads)
                
                # Acknowledge the entire batch in Redis
                for msg_id in msg_ids:
                    redis_client.xack(self.stream_name, self.group_name, msg_id)
            except Exception as e:
                print(f"Error processing batch of size {len(msg_ids)}: {e}")
