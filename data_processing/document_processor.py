import io
import uuid
from pathlib import Path
from typing import Any, Dict, List

import fitz
import numpy as np
from PIL import Image
from rapidocr_onnxruntime import RapidOCR

from core.config import Config
from core.interfaces.embedding_provider import EmbeddingProviderInterface
from core.interfaces.vector_store import VectorStoreInterface
from data_processing.chunkers.semantic_chunker import SemanticChunker


class PDFParser:
    def __init__(self):
        self.ocr_engine = RapidOCR()

    def extract_text_from_page(self, page) -> str:
        text = page.get_text("text")
        if len(text.strip()) > 50:
            return text

        pix = page.get_pixmap(dpi=200)
        image = Image.open(io.BytesIO(pix.tobytes("png")))
        result, _ = self.ocr_engine(np.array(image))
        if not result:
            return ""
        return "\n".join(x[1] for x in result)

    def parse_pdf(self, pdf_path: str) -> list[dict]:
        doc = fitz.open(pdf_path)
        pages = []
        for page_num in range(len(doc)):
            pages.append(
                {
                    "page": page_num + 1,
                    "text": self.extract_text_from_page(doc[page_num]),
                }
            )
        return pages


class DocumentProcessor:
    def __init__(
        self,
        config: Config,
        embedding_provider: EmbeddingProviderInterface,
        vector_store: VectorStoreInterface,
    ):
        self.config = config
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.parser = PDFParser()
        self.chunker = SemanticChunker(embedding_provider=self.embedding_provider)

    def parse_and_chunk(self, file_path: str, source_type: str, document_id: str) -> List[Dict[str, Any]]:
        pdf_path = Path(file_path)
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
                all_chunks.append(
                    {
                        "text": chunk_text,
                        "source_type": source_type,
                        "source_file": pdf_path.name,
                        "page": page_num,
                        "heading": current_heading,
                        "chunk_id": f"{document_id}_{chunk_idx}",
                        "document_id": document_id,
                    }
                )
                chunk_idx += 1

        return all_chunks

    def process_document(self, file_path: str, source_type: str, owner_id: str, document_id: str) -> None:
        """Parse → chunk → embed → upsert in one go with real-time progress tracking."""
        from api.services.progress_manager import DocumentProgressManager
        progress = DocumentProgressManager()
        
        progress.start_chunking(document_id)
        all_chunks = self.parse_and_chunk(file_path, source_type, document_id)
        
        if not all_chunks:
            progress.finish(document_id)
            return

        total_chunks = len(all_chunks)
        progress.initialize_embedding(document_id, total_chunks)

        collection = (
            self.config.TEXTBOOK_COLLECTION_NAME
            if source_type == "textbook"
            else self.config.SLIDES_COLLECTION_NAME
        )

        batch_size = 5
        import uuid
        for i in range(0, total_chunks, batch_size):
            batch = all_chunks[i:i + batch_size]
            texts = [c["text"] for c in batch]
            embeddings = self.embedding_provider.embed_batch(texts)
            
            points = []
            for chunk_meta, vector in zip(batch, embeddings):
                chunk_meta["owner_id"] = owner_id
                points.append({"id": str(uuid.uuid4()), "vector": vector, "payload": chunk_meta})
            
            self.vector_store.upsert(collection, points)
            
            # Emit progress for each chunk in the batch
            for _ in range(len(batch)):
                progress.complete_chunk(document_id)
