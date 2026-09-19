import uuid
from typing import Any, Dict

from core.config import Config
from core.interfaces.embedding_provider import EmbeddingProviderInterface
from core.interfaces.vector_store import VectorStoreInterface
from workers.base_worker import BaseWorker
from api.services.progress_manager import DocumentProgressManager

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
        self.progress = DocumentProgressManager()

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
        
        # Advance the progress bar for this specific chunk
        self.progress.complete_chunk(payload["document_id"])
        print(f"Upserted chunk {payload['chunk_id']} to Qdrant.")

    def process_batch(self, payloads: list[Dict[str, Any]]):
        if not payloads:
            return
            
        print(f"Embedding batch of {len(payloads)} chunks...")
        
        texts = [p["text"] for p in payloads]
        vectors = self.embedding_provider.embed_batch(texts) 
        
        textbook_points = []
        slides_points = []
        
        for i, payload in enumerate(payloads):
            point = {"id": str(uuid.uuid4()), "vector": vectors[i], "payload": payload}
            if payload.get("source_type") == "textbook":
                textbook_points.append(point)
            else:
                slides_points.append(point)
                
        if textbook_points:
            self.vector_store.upsert(self.config.TEXTBOOK_COLLECTION_NAME, textbook_points)
        if slides_points:
            self.vector_store.upsert(self.config.SLIDES_COLLECTION_NAME, slides_points)
            
        for payload in payloads:
            self.progress.complete_chunk(payload["document_id"])
            
        print(f"Upserted {len(payloads)} chunks to Qdrant.")


if __name__ == "__main__":
    from core.providers.sentence_transformer_provider import SentenceTransformerProvider
    from db.qdrant_store import QdrantVectorStore

    print("Booting EmbeddingWorker... loading model...")
    config = Config()
    
    embedding_provider = SentenceTransformerProvider("all-MiniLM-L6-v2")
    vector_store = QdrantVectorStore(config)
    
    worker = EmbeddingWorker(
        config=config,
        embedding_provider=embedding_provider,
        vector_store=vector_store
    )
    worker.run_batch(worker.process_batch, batch_size=32)
