import json
import os
from datetime import datetime
from pathlib import Path

from core.redis import redis_client


UPLOAD_WEIGHT = 5
QUEUE_WEIGHT = 5
CHUNKING_WEIGHT = 15
EMBEDDING_WEIGHT = 70
FINALIZING_WEIGHT = 5


class DocumentProgressManager:

    def __init__(self):
        self.redis = redis_client

    def _key(self, document_id):
        return f"doc:{document_id}"

    def create(self, document_id, owner_id, path):
        now = datetime.utcnow().isoformat()

        self.redis.hset(
            self._key(document_id),
            mapping={
                "document_id": document_id,
                "owner_id": owner_id,
                "path": path,

                "status": "queued",
                "stage": "queued",

                "total_chunks": 0,
                "completed_chunks": 0,

                "progress": UPLOAD_WEIGHT,

                "created_at": now,
                "updated_at": now,

                "error": ""
            }
        )

    def start_chunking(self, document_id):
        self.redis.hset(
            self._key(document_id),
            mapping={
                "status": "processing",
                "stage": "chunking",
                "progress": UPLOAD_WEIGHT + QUEUE_WEIGHT,
                "updated_at": datetime.utcnow().isoformat()
            }
        )

    def initialize_embedding(self, document_id, total_chunks):
        self.redis.hset(
            self._key(document_id),
            mapping={
                "stage": "embedding",
                "total_chunks": total_chunks,
                "completed_chunks": 0,
                "progress": 25,
                "updated_at": datetime.utcnow().isoformat()
            }
        )

    def _publish(self, document_id):
        data = self.get(document_id)

        self.redis.publish(
            f"progress:{document_id}",
            json.dumps(data)
        )

    def get(self, document_id):
        data = self.redis.hgetall(self._key(document_id))

        if not data:
            return None

        result = {}

        for k, v in data.items():

            if isinstance(k, bytes):
                k = k.decode()

            if isinstance(v, bytes):
                v = v.decode()

            result[k] = v

        return result
    
    def complete_chunk(self, document_id):
        key = self._key(document_id)

        completed = self.redis.hincrby(
            key,
            "completed_chunks",
            1
        )

        total = int(
            self.redis.hget(
                key,
                "total_chunks"
            )
        )

        overall = (
            UPLOAD_WEIGHT
            + QUEUE_WEIGHT
            + CHUNKING_WEIGHT
            + (completed / total) * EMBEDDING_WEIGHT
        )

        self.redis.hset(
            key,
            mapping={
                "progress": round(overall, 2),
                "updated_at": datetime.utcnow().isoformat()
            }
        )

        self._publish(document_id)

        if completed >= total:
            self.finish(document_id)

    def finish(self, document_id):
        key = self._key(document_id)

        path = self.redis.hget(
            key,
            "path"
        )

        if isinstance(path, bytes):
            path = path.decode()

        try:

            Path(path).unlink(
                missing_ok=True
            )

        except Exception as e:

            print(e)

        self.redis.hset(
            key,
            mapping={
                "stage":"completed",
                "status":"completed",
                "progress":100,
                "updated_at":datetime.utcnow().isoformat()
            }
        )

        self.redis.expire(
            self._key(document_id),
            60 * 60 * 24
        )

        self._publish(document_id)