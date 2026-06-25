import re

import nltk
from sentence_transformers import SentenceTransformer

_EMBED_MODEL = None
_NLTK_READY = False

HEADING_PATTERNS = [
    r"^chapter\s+\d+",
    r"^unit\s+\d+",
    r"^section\s+\d+",
    r"^\d+\.\d+",
    r"\d+\.\d+\.\d+",
]


def _ensure_sentence_tokenizer():
    global _NLTK_READY

    if _NLTK_READY:
        return

    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt", quiet=True)

    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        nltk.download("punkt_tab", quiet=True)

    _NLTK_READY = True


def _get_embed_model():
    global _EMBED_MODEL

    if _EMBED_MODEL is None:
        _EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")

    return _EMBED_MODEL


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
        _ensure_sentence_tokenizer()
        return nltk.sent_tokenize(text)

    def cosine_similarity(self, a, b):
        return (a @ b) / ((a @ a) ** 0.5 * (b @ b) ** 0.5)

    def semantic_merge(self, sentences):
        if not sentences:
            return []

        embeddings = _get_embed_model().encode(sentences)
        chunks = []

        current_chunk = [sentences[0]]
        current_words = len(sentences[0].split())

        for index in range(1, len(sentences)):
            prev_emb = embeddings[index - 1]
            curr_emb = embeddings[index]

            similarity = self.cosine_similarity(prev_emb, curr_emb)
            sentence_words = len(sentences[index].split())

            if (similarity > self.similarity_threshold and
                    current_words + sentence_words <= self.max_chunk_words):
                current_chunk.append(sentences[index])
                current_words += sentence_words
            else:
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentences[index]]
                current_words = sentence_words

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks
