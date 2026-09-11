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

    _, entries_raw = messages[0]

    # Some versions of redis-py return a dict, others a list of tuples
    if isinstance(entries_raw, dict):
        entries = list(entries_raw.items())
    else:
        entries = entries_raw

    for entry in entries:
        if len(entry) != 2:
            continue
            
        msg_id, data = entry
        
        # If data is returned as a flat list instead of a dict
        if isinstance(data, list):
            data = {data[i]: data[i+1] for i in range(0, len(data), 2)}

        # Handle string or bytes keys depending on decode_responses
        payload_str = data.get("data") or data.get(b"data")
        if not payload_str:
            continue
            
        if isinstance(payload_str, bytes):
            payload_str = payload_str.decode('utf-8')

        payload = json.loads(payload_str)
        
        try:
            progress.start_chunking(payload["document_id"])

            chunks = build_chunks(payload["path"], payload["source_type"])

            print("chunks built")
            
            if not chunks:
                print(f"No chunks produced for {payload['document_id']}, finishing early.")
                progress.initialize_embedding(payload["document_id"], 0)
                progress.finish(payload["document_id"])
            else:
                progress.initialize_embedding(payload["document_id"], len(chunks))

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
                
        except Exception as e:
            print(f"Error processing {payload['document_id']}: {e}")
            progress.finish(payload["document_id"])

        redis_client.xack(
            "document_ingestion",
            GROUP,
            msg_id
        )