import json
from pathlib import Path
from typing import Any, Dict

from core.redis import redis_client
from ingestion.parser import PDFParser
from data_processing.chunkers.semantic_chunker import SemanticChunker
from core.interfaces.embedding_provider import EmbeddingProviderInterface
from workers.base_worker import BaseWorker
from api.services.progress_manager import DocumentProgressManager

class ChunkWorker(BaseWorker):
    def __init__(self, chunker: SemanticChunker):
        super().__init__(
            group_name="chunkers",
            consumer_name="chunk_worker_1",
            stream_name="document_processing",
        )
        self.parser = PDFParser()
        self.chunker = chunker
        self.progress = DocumentProgressManager()

    def process_message(self, payload: Dict[str, Any]):
        document_id = payload["document_id"]
        print(f"Chunking document: {payload['filename']}")
        
        self.progress.start_chunking(document_id)
        
        pdf_path = Path(payload["path"])
        pages = self.parser.parse_pdf(str(pdf_path))

        all_chunks = []
        current_heading = "Unknown"
        chunk_idx = 0

        for page_data in pages:
            page_num = page_data["page"]
            cleaned_lines = []
            for line in page_data["text"].split("\n"):
                stripped = line.strip()
                if not stripped:
                    continue
                if self.chunker.is_heading(stripped):
                    current_heading = stripped
                cleaned_lines.append(stripped)

            sentences = self.chunker.sentence_split(" ".join(cleaned_lines))
            for chunk_text in self.chunker.semantic_merge(sentences):
                chunk = {
                    "text": chunk_text,
                    "source_type": payload.get("source_type", "textbook"),
                    "source_file": payload["filename"],
                    "page": page_num,
                    "heading": current_heading,
                    "chunk_id": f"{document_id}_{chunk_idx}",
                    "document_id": document_id,
                    "owner_id": payload["owner_id"]
                }
                all_chunks.append(chunk)
                
                # Push individual chunk to embedding queue
                redis_client.xadd("embedding_queue", {"data": json.dumps(chunk)})
                chunk_idx += 1

        self.progress.initialize_embedding(document_id, len(all_chunks))
        print(f"Sent {len(all_chunks)} chunks to embedding queue.")


if __name__ == "__main__":
    from core.providers.sentence_transformer_provider import SentenceTransformerProvider
    # Semantic chunker requires embeddings to merge meaningfully
    embedding_provider = SentenceTransformerProvider("all-MiniLM-L6-v2")
    chunker = SemanticChunker(embedding_provider=embedding_provider)
    
    worker = ChunkWorker(chunker=chunker)
    worker.run(worker.process_message)
