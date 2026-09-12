import uuid
from typing import Any, Dict

from core.config import Config
from core.interfaces.embedding_provider import EmbeddingProviderInterface
from core.interfaces.vector_store import VectorStoreInterface
from workers.base_worker import BaseWorker


class EmbeddingWorker(BaseWorker):
    def __init__(
        self,
        config: Config,
        embedding_provider: EmbeddingProviderInterface,
        vector_store: VectorStoreInterface,
    ):
        super().__init__(
            group_name="embedders",
            consumer_name="embedding_worker_1",
            stream_name="embedding_queue",
        )
        self.config = config
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store

    def process_message(self, payload: Dict[str, Any]):
        print(f"Embedding chunk: {payload['chunk_id']}")
        vector = self.embedding_provider.embed_text(payload["text"])
        collection = (
            self.config.TEXTBOOK_COLLECTION_NAME
            if payload.get("source_type") == "textbook"
            else self.config.SLIDES_COLLECTION_NAME
        )
        self.vector_store.upsert(
            collection,
            [{"id": str(uuid.uuid4()), "vector": vector, "payload": payload}],
        )
        print("Upserted chunk to Qdrant.")


if __name__ == "__main__":
    pass
