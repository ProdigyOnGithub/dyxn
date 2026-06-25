import logging
import re

import fitz

from chunking.parser import PDFParser

SEMANTIC_THRESHOLD = 0.55
BM25_THRESHOLD = 2
TOP_K_NOTES = 5

logger = logging.getLogger(__name__)
parser = PDFParser()


def cosine_similarity(a, b):
    return (a @ b) / ((a @ a) ** 0.5 * (b @ b) ** 0.5)


def extract_toc(pdf_path):
    doc = fitz.open(pdf_path)
    toc = doc.get_toc()

    parsed = []

    for entry in toc:
        level, title, book_page = entry
        parsed.append(
            {
                "level": level,
                "title": title,
                "page": book_page,
            }
        )

    return parsed


def is_toc_page(text):
    text_lower = text.lower()
    toc_indicators = ["table of contents", "contents", "content", "index"]

    for indicator in toc_indicators:
        if indicator in text_lower:
            return True

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
    toc_pages = []

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

                toc_entries.append(
                    {
                        "title": title,
                        "book_page": book_page,
                    }
                )

                continue

            numbered_match = numbered_pattern.match(line)

            if numbered_match:
                section_number = numbered_match.group(1)
                title = numbered_match.group(3)
                book_page = int(numbered_match.group(4))

                full_title = f"{section_number} {title}"

                toc_entries.append(
                    {
                        "title": full_title,
                        "book_page": book_page,
                    }
                )

    unique_entries = []
    seen = set()

    for entry in toc_entries:
        key = (entry["title"], entry["book_page"])

        if key not in seen:
            seen.add(key)
            unique_entries.append(entry)

    unique_entries = sorted(unique_entries, key=lambda x: x["book_page"])

    return unique_entries


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting TOC extraction")
    logger.info("TOC entries=%s", extract_toc("data/TOC.pdf"))
