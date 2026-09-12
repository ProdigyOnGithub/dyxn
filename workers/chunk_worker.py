import json
from typing import Any, Dict

from core.redis import redis_client
from data_processing.document_processor import DocumentProcessor
from workers.base_worker import BaseWorker


class ChunkWorker(BaseWorker):
    def __init__(self, document_processor: DocumentProcessor):
        super().__init__(
            group_name="chunkers",
            consumer_name="chunk_worker_1",
            stream_name="document_processing",
        )
        self.document_processor = document_processor

    def process_message(self, payload: Dict[str, Any]):
        print(f"Chunking document: {payload['filename']}")
        chunks = self.document_processor.parse_and_chunk(
            file_path=payload["path"],
            source_type=payload.get("source_type", "textbook"),
            document_id=payload["document_id"],
        )
        for chunk in chunks:
            chunk["owner_id"] = payload["owner_id"]
            redis_client.xadd("embedding_queue", {"data": json.dumps(chunk)})
        print(f"Sent {len(chunks)} chunks to embedding queue.")


if __name__ == "__main__":
    # need DocumentProcessor (parser + embeddings) before this can run
    pass
