from typing import List

from core.interfaces.embedding_provider import EmbeddingProviderInterface


class MockEmbeddingProvider(EmbeddingProviderInterface):
    def __init__(self, dimension: int = 768):
        self.dimension = dimension

    def embed_text(self, text: str) -> List[float]:
        return [0.0] * self.dimension

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [[0.0] * self.dimension for _ in texts]
