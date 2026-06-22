import json
from core.redis import redis_client
from ingestion.embedding import embed_text
from ingestion.ingest import upsert_chunk

GROUP = "embedders"
CONSUMER = "embedder_1"

try:
    redis_client.xgroup_create(
        "embedding_queue",
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
        {"embedding_queue": ">"},
        count=1,
        block=5000
    )

    if not messages:
        continue

    _, entries = messages[0]

    for msg_id, data in entries:

        payload = json.loads(data["data"])
        vector = embed_text([payload["text"]])[0]
        chunk_id = (f"{payload['document_id']}_{payload['chunk_index']}")

        upsert_chunk(
            chunk_id=chunk_id,
            embedding=vector,
            payload={
                "owner_id": payload["owner_id"],
                "document_id": payload["document_id"],
                "chunk_index": payload["chunk_index"],
                "source_type": payload["source_type"],
                "text": payload["text"]
            }
        )

        redis_client.xack(
            "embedding_queue",
            GROUP,
            msg_id
        )