import json
from core.redis import redis_client
from chunking.pipeline import build_chunks
import uuid
from task_queue.progress import DocumentProgressManager


progress = DocumentProgressManager()

GROUP = "chunkers"
CONSUMER = "worker_1"

try:
    redis_client.xgroup_create(
        "document_ingestion",
        GROUP,
        id="0",
        mkstream=True
    )
except:
    pass

while True:

    messages = redis_client.xreadgroup(
        GROUP,
        CONSUMER,
        {"document_ingestion": ">"},
        count=1,
        block=0
    )

    if not messages:
        continue

    _, entries = messages[0]

    for msg_id, data in entries:

        payload = json.loads(data["data"])

        progress.start_chunking(payload["document_id"])

        chunks = build_chunks(payload["path"], payload["source_type"])

        print(chunks)
        progress.initialize_embedding(payload["document_id"], len(chunks))
        print("chunks built")

        for i,chunk in enumerate(chunks):
            print(i,chunk)
            embed_id = redis_client.xadd(
                "embedding_queue",
                {
                    "data":json.dumps({
                        "document_id":payload["document_id"],
                        "owner_id":payload["owner_id"],
                        "chunk_index":i,
                        "source_type":payload["source_type"],
                        "text":chunk["text"],
                        "source_file":chunk.get("source_file",""),
                        "page":chunk.get("page"),
                        "heading":chunk.get("heading","")
                    })
                }
            )        
            print("Chunk sent:", embed_id)
        print("chunks sent")

        redis_client.xack(
            "document_ingestion",
            GROUP,
            msg_id
        )