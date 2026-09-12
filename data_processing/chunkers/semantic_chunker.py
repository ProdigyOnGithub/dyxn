import re

import nltk

from core.interfaces.embedding_provider import EmbeddingProviderInterface

try:
    nltk.data.find("tokenizers/punkt")
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt")
    nltk.download("punkt_tab")

HEADING_PATTERNS = [
    r"^chapter\s+\d+",
    r"^unit\s+\d+",
    r"^section\s+\d+",
    r"^\d+\.\d+",
    r"\d+\.\d+\.\d+",
]


class SemanticChunker:
    def __init__(
        self,
        embedding_provider: EmbeddingProviderInterface,
        max_chunk_words: int = 300,
        similarity_threshold: float = 0.72,
    ):
        self.embedding_provider = embedding_provider
        self.max_chunk_words = max_chunk_words
        self.similarity_threshold = similarity_threshold

    def is_heading(self, text: str) -> bool:
        cleaned = text.strip().lower()
        return any(re.match(p, cleaned) for p in HEADING_PATTERNS)

    def sentence_split(self, text: str) -> list[str]:
        return nltk.sent_tokenize(text)

    def cosine_similarity(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = sum(x * x for x in a) ** 0.5
        mag_b = sum(x * x for x in b) ** 0.5
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    def semantic_merge(self, sentences: list[str]) -> list[str]:
        if not sentences:
            return []

        embeddings = self.embedding_provider.embed_batch(sentences)
        chunks = []
        current_chunk = [sentences[0]]
        current_words = len(sentences[0].split())

        for i in range(1, len(sentences)):
            similarity = self.cosine_similarity(embeddings[i - 1], embeddings[i])
            sentence_words = len(sentences[i].split())
            if similarity > self.similarity_threshold and current_words + sentence_words <= self.max_chunk_words:
                current_chunk.append(sentences[i])
                current_words += sentence_words
            else:
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentences[i]]
                current_words = sentence_words

        if current_chunk:
            chunks.append(" ".join(current_chunk))
        return chunks
