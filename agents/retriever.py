from typing import Any, Dict

from agents.base_agent import BaseAgent
from core.config import Config
from core.interfaces.embedding_provider import EmbeddingProviderInterface
from core.interfaces.llm_provider import LLMProviderInterface
from core.interfaces.vector_store import VectorStoreInterface


class RetrieverAgent(BaseAgent):
    def __init__(
        self,
        llm: LLMProviderInterface,
        config: Config,
        vector_store: VectorStoreInterface,
        embedding_provider: EmbeddingProviderInterface,
    ):
        super().__init__(llm, config)
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query = state.get("syllabus_topic", "")
        try:
            query_vector = self.embedding_provider.embed_text(query)
        except Exception as e:
            self.logger.error(f"Failed to embed query: {e}")
            return state

        results = []
        for collection in (self.config.TEXTBOOK_COLLECTION_NAME, self.config.SLIDES_COLLECTION_NAME):
            if not collection:
                continue
            try:
                results.extend(self.vector_store.search(collection, query_vector, limit=10))
            except Exception as e:
                self.logger.error(f"Retrieval failed for {collection}: {e}")

        seen = set()
        unique = []
        for doc in results:
            text = doc.get("payload", {}).get("text", "")
            if text and text not in seen:
                unique.append(doc)
                seen.add(text)

        state["retrieved_chunks"] = [d.get("payload", {}).get("text", "") for d in unique]
        state["retrieved_metadata"] = [d.get("payload", {}) for d in unique]
        return state
