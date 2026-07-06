import json
from core.redis import redis_client
from task_queue.progress import DocumentProgressManager


def enqueue_document(document_id: str, owner_id: str, path: str, source_type: str):
    redis_client.xadd(
        "document_ingestion",
        {
            "data": json.dumps({
                "document_id": document_id,
                "owner_id": owner_id,
                "path": path,
                "source_type": source_type
            })
        }
    )

    progress = DocumentProgressManager()

    progress.create(
        document_id=document_id,
        owner_id=owner_id,
        path=path
    )