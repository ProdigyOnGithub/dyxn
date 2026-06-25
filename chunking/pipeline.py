import json
import logging
from pathlib import Path

from chunking.chunker import SemanticChunker
from chunking.parser import PDFParser

logger = logging.getLogger(__name__)
chunker = SemanticChunker(max_chunk_words=300, similarity_threshold=0.72)
parser = PDFParser()


def _resolve_pdf_files(input_path):
    path = Path(input_path)

    if not path.exists():
        raise FileNotFoundError(f"Input path does not exist: {path}")

    if path.is_file():
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Expected a PDF file, got: {path}")
        return [path]

    pdf_files = sorted(
        file_path
        for file_path in path.iterdir()
        if file_path.is_file() and file_path.suffix.lower() == ".pdf"
    )

    if not pdf_files:
        raise ValueError(f"No PDF files found in directory: {path}")

    return pdf_files


def _build_chunks_from_pdf_files(pdf_files, source_type):
    all_chunks = []

    for pdf_path in pdf_files:
        logger.info("Processing PDF %s", pdf_path.name)
        pages = parser.parse_pdf(str(pdf_path))
        current_heading = "Unknown"

        for page_data in pages:
            page_num = page_data["page"]
            text = page_data["text"]
            lines = text.split("\n")
            
            cleaned_lines = []

            for line in lines:
                stripped = line.strip()

                if not stripped:
                    continue

                if chunker.is_heading(stripped):
                    current_heading = stripped

                cleaned_lines.append(stripped)

            merged_text = " ".join(cleaned_lines)
            sentences = chunker.sentence_split(merged_text)
            semantic_chunks = chunker.semantic_merge(sentences)

            for idx, chunk in enumerate(semantic_chunks):
                all_chunks.append(
                    {
                        "source_type": source_type,
                        "source_file": pdf_path.name,
                        "page": page_num,
                        "heading": current_heading,
                        "chunk_id": f"{pdf_path.stem}_{page_num}_{idx}",
                        "text": chunk,
                    }
                )

    return all_chunks


def build_file_chunks(input_dir, output_path, source_type):
    all_chunks = build_chunks(input_dir, source_type)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    logger.info("Saved chunks count=%s output_path=%s", len(all_chunks), output_path)


def build_chunks(input_path, source_type):
    pdf_files = _resolve_pdf_files(input_path)
    return _build_chunks_from_pdf_files(pdf_files, source_type)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build_file_chunks(input_dir="data/", output_path="data/textbook_chunks.json", source_type="textbook")
