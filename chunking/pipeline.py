import io
import re
import json
from pathlib import Path

import fitz
import nltk
import numpy as np

from PIL import Image
from rapidocr_onnxruntime import RapidOCR
from sentence_transformers import SentenceTransformer

from chunker import SemanticChunker
from parser import PDFParser

nltk.download('punkt')

EMBED_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
OCR_ENGINE = RapidOCR()

HEADING_PATTERNS = [
    r"^chapter\s+\d+",
    r"^unit\s+\d+",
    r"^section\s+\d+",
    r"^\d+\.\d+",
    r"\d+\.\d+\.\d+"
]

chunker = SemanticChunker(max_chunk_words=300, similarity_threshold=0.72)
parser = PDFParser()

def build_chunks(input_dir, output_path, source_type):
    all_chunks=[]
    pdf_files = list(Path(input_dir).glob("*.pdf"))
    print("found file")

    for pdf_path in pdf_files:
        print(f"Processing {pdf_path.name}")

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
                all_chunks.append({
                    "source_type": source_type,
                    "source_file": pdf_path.name,
                    "page": page_num,
                    "heading": current_heading,
                    "chunk_id": f"{pdf_path.stem}_{page_num}_{idx}",
                    "text": chunk
                })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            all_chunks,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(f"Saved {len(all_chunks)} chunks")

build_chunks(input_dir="data/", output_path="data/textbook_chunks.json", source_type="textbook")

# build_chunks(input_dir="raw_data/notes", output_path="data/notes_chunks.json", source_type="notes")