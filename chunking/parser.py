import io

import fitz
import numpy as np
from PIL import Image

_OCR_ENGINE = None


def _get_ocr_engine():
    global _OCR_ENGINE

    if _OCR_ENGINE is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError as exc:
            raise RuntimeError(
                "RapidOCR could not be imported. Ensure the Docker image has OCR/OpenCV "
                "runtime dependencies installed."
            ) from exc

        _OCR_ENGINE = RapidOCR()

    return _OCR_ENGINE


def _run_ocr(image_np):
    engine = _get_ocr_engine()

    if hasattr(engine, "ocr"):
        output = engine.ocr(image_np)
    elif callable(engine):
        output = engine(image_np)
    else:
        raise RuntimeError("RapidOCR engine is not callable and has no 'ocr' method.")

    if isinstance(output, tuple):
        return output[0] or []

    return output or []


def _ocr_item_text(item):
    if isinstance(item, dict):
        value = item.get("text") or item.get("rec_text") or item.get("content") or item.get("value")
    elif isinstance(item, (list, tuple)) and len(item) >= 2:
        value = item[1]
    else:
        value = item

    if isinstance(value, dict):
        value = value.get("text") or value.get("rec_text") or value.get("content") or value.get("value")

    if isinstance(value, (list, tuple)) and value:
        value = value[0]

    return str(value).strip() if value is not None else ""


def _ocr_text(result):
    lines = [_ocr_item_text(item) for item in result]
    return "\n".join(line for line in lines if line)


class PDFParser:
    def extract_text_from_page(self, page):
        text = page.get_text("text")
        if len(text.strip()) > 50:
            return text

        pix = page.get_pixmap(dpi=200)
        image = Image.open(io.BytesIO(pix.tobytes("png")))
        image_np = np.array(image)
        result = _run_ocr(image_np)

        return _ocr_text(result)

    def parse_pdf(self, pdf_path):
        doc = fitz.open(pdf_path)
        pages = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = self.extract_text_from_page(page)
            pages.append(
                {
                    "page": page_num + 1,
                    "text": text,
                }
            )

        return pages
