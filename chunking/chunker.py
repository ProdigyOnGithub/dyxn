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

class SemanticChunker:

    def __init__(self, max_chunk_words=300, similarity_threshold=0.72):
        self.max_chunk_words = max_chunk_words
        self.similarity_threshold = similarity_threshold

    def is_heading(self, text):

        cleaned = text.strip().lower()

        for pattern in HEADING_PATTERNS:
            if re.match(pattern, cleaned):
                return True
        
        return False
    
    def sentence_split(self, text):
        return nltk.sent_tokenize(text)
    
    def cosine_similarity(self, a, b):
        return (
            a @ b
        ) / (
            (a@a)**0.5 *
            (b@b)**0.5
        )
    
    def semantic_merge(self, sentences):
        if not sentences:
            return []
        
        embeddings = EMBED_MODEL.encode(sentences)
        chunks=[]

        current_chunk=[sentences[0]]
        current_words = len(sentences[0].split())

        for i in range(1, len(sentences)):
            prev_emb = embeddings[i-1]
            curr_emb = embeddings[i]

            similarity = self.cosine_similarity(prev_emb, curr_emb)

            sentence_words = len(sentences[i].split())

            if (similarity > self.similarity_threshold and
                current_words+sentence_words <= self.max_chunk_words):
                current_chunk.append(sentences[i])
                current_words += sentence_words
            else:
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentences[i]]
                current_words = sentence_words

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks