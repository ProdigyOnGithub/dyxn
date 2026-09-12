import json
from datetime import datetime
from pathlib import Path
from core.redis import redis_client

UPLOAD_WEIGHT = 5
QUEUE_WEIGHT = 5
CHUNKING_WEIGHT = 15
EMBEDDING_WEIGHT = 70
FINALIZING_WEIGHT = 5

class DocumentProgressManager:
    """
    Manages document processing progress state in Redis hashes and emits PubSub events.
    """
    def __init__(self):
        self.redis = redis_client

    def _key(self, document_id: str) -> str:
        return f"doc:{document_id}"

    def create(self, document_id: str, owner_id: str, path: str):
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
        self._publish(document_id)

    def start_chunking(self, document_id: str):
        self.redis.hset(
            self._key(document_id),
            mapping={
                "status": "processing",
                "stage": "chunking",
                "progress": UPLOAD_WEIGHT + QUEUE_WEIGHT,
                "updated_at": datetime.utcnow().isoformat()
            }
        )
        self._publish(document_id)

    def initialize_embedding(self, document_id: str, total_chunks: int):
        self.redis.hset(
            self._key(document_id),
            mapping={
                "stage": "embedding",
                "total_chunks": total_chunks,
                "completed_chunks": 0,
                "progress": UPLOAD_WEIGHT + QUEUE_WEIGHT + CHUNKING_WEIGHT,
                "updated_at": datetime.utcnow().isoformat()
            }
        )
        self._publish(document_id)

    def complete_chunk(self, document_id: str):
        key = self._key(document_id)
        completed = self.redis.hincrby(key, "completed_chunks", 1)
        
        total_raw = self.redis.hget(key, "total_chunks")
        if not total_raw:
            return
            
        total = int(total_raw)
        
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

    def finish(self, document_id: str):
        key = self._key(document_id)
        path_raw = self.redis.hget(key, "path")
        
        if isinstance(path_raw, bytes):
            path = path_raw.decode()
        else:
            path = path_raw

        try:
            if path:
                p = Path(path)
                if p.exists():
                    p.unlink()
                    print(f"Successfully deleted processed file: {path}")
        except Exception as e:
            print(f"Failed to delete file {path}: {e}")

        self.redis.hset(
            key,
            mapping={
                "stage": "completed",
                "status": "completed",
                "progress": 100.0,
                "updated_at": datetime.utcnow().isoformat()
            }
        )
        
        self.redis.expire(key, 60 * 60 * 24) # expire in 24 hrs
        self._publish(document_id)

    def get(self, document_id: str) -> dict:
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

    def _publish(self, document_id: str):
        data = self.get(document_id)
        if data:
            self.redis.publish(f"progress:{document_id}", json.dumps(data))
