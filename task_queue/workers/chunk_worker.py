import json
from core.redis import redis_client
from chunking.pipeline import build_chunks
import uuid

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
        chunks = build_chunks(payload["path"], payload["source_type"])
        print(chunks)
        print("chunks built")

        for i, chunk in enumerate(chunks):
            print(i, chunk)
            msg_id = redis_client.xadd(
                "embedding_queue",
                {
                    "data": json.dumps({
                        "document_id": payload["document_id"],
                        "owner_id": payload["owner_id"],
                        "chunk_index": i,
                        "source_type": payload["source_type"], 
                        "text": chunk["text"]
                    })
                }
            )
            print("Chunk sent:", msg_id)
        print("chunks sent")

        redis_client.xack(
            "document_ingestion",
            GROUP,
            msg_id
        )