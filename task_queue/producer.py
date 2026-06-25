import json

from core.redis import redis_client


def enqueue_document(document_id: str, owner_id: str, path: str, source_type: str):
    payload = {
        "document_id": document_id,
        "owner_id": owner_id,
        "path": path,
        "source_type": source_type,
    }
    redis_client.xadd(
        "document_ingestion",
        {"data": json.dumps(payload)},
    )
