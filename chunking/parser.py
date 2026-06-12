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

class PDFParser:

    def extract_text_from_page(self, page):

        text=page.get_text("text")
        if len(text.strip()) > 50:
            return text
        
        pix = page.get_pixmap(dpi=200)

        image = Image.open(io.BytesIO(pix.tobytes("png")))

        image_np = np.array(image)

        result, _ = OCR_ENGINE.ocr(image_np)

        return "\n".join([x[1] for x in result])
    
    def parse_pdf(self, pdf_path):

        doc = fitz.open(pdf_path)

        pages = []

        for page_num in range(len(doc)):
            page = doc[page_num]

            text = self.extract_text_from_page(page)

            pages.append({
                "page":page_num+1,
                "text":text
            })

        return pages