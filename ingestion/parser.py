import io
import numpy as np
from PIL import Image
import pymupdf as fitz
from rapidocr_onnxruntime import RapidOCR

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
