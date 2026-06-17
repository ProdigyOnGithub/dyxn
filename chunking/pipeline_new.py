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

print("Done importing")

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

SEMANTIC_THRESHOLD = 0.55
BM25_THRESHOLD = 2
TOP_K_NOTES = 5

chunker = SemanticChunker(max_chunk_words=300, similarity_threshold=0.72)
parser = PDFParser()

def cosine_similarity(a, b):
    return (
        a @ b
    ) / (
        (a@a)**0.5 *
        (b@b)**0.5
    )

def extract_toc(pdf_path):
    doc = fitz.open(pdf_path)
    if doc:
        print("Doc found")
    toc = doc.get_toc()
    print(doc)

    parsed = []
    
    for idx, entry in enumerate(toc):
        level, title, book_page = entry
        parsed.append({
            "level": level,
            "title": title,
            "page": book_page
        })

    return parsed

print("Start toc extraction")
print(extract_toc("data/TOC.pdf"))

def is_toc_page(text):
    text_lower = text.lower()
    TOC_INDICATORS = ["table of contents", "contents", "content", "index"]

    for indicator in TOC_INDICATORS:
        if indicator in text_lower:
            return True
    
    # some weird ahh logic
    lines = text.split("\n")
    dotted_lines = 0
    numbered_lines = 0

    for line in lines:
        line = line.strip()

        if re.search(r"\.{2,}", line):
            dotted_lines += 1

        if re.search(r"\d+\s*$", line):
            numbered_lines += 1

    if dotted_lines >= 5:
        return True
    
    if numbered_lines >= 8:
        return True
    
    return False

def find_toc_pages(pdf_path, search_pages=25):
    pages = parser.parse_pdf(pdf_path)

    toc_pages=[]

    for page in pages[:search_pages]:
        if is_toc_page(page["text"]):
            toc_pages.append(page)

    return toc_pages

def parse_toc_entries(toc_pages):
    toc_entries = []

    dotted_pattern = re.compile(
        r"^(.*?)\s+\.{2,}\s*(\d+)\s*$"
    )

    numbered_pattern = re.compile(
        r"^(\d+(\.\d+)*)\s+(.*?)\s+(\d+)\s*$"
    )

    for toc_page in toc_pages:
        lines = toc_page["text"].split("\n")

        for line in lines:
            line = line.strip()

            if not line:
                continue

            dotted_match = dotted_pattern.match(line)

            if dotted_match:
                title = dotted_match.group(1)
                book_page = int(dotted_match.group(2))

                toc_entries.append({
                    "title": title,
                    "book_page": book_page
                })

                continue

            numbered_match = numbered_pattern.match(line)

            if numbered_match:

                section_number = numbered_match.group(1)
                title =  numbered_match.group(3)
                book_page = int(numbered_match.group(4))

                full_title = (f"{section_number} {title}")

                toc_entries.append({
                    "title": full_title,
                    "book_page": book_page
                })

    unique_entries = []
    seen = set()

    for entry in toc_entries:
        key = (entry["title"], entry["book_page"])

        if key not in seen:
            seen.add(key)
            unique_entries.append(entry)
    
    unique_entries = sorted(
        unique_entries,
        key=lambda x: x["book_page"]
    )
    
    return unique_entries