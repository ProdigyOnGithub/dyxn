from typing import Any, Dict, List

from agents.base_agent import BaseAgent
from core.config import Config
from core.interfaces.embedding_provider import EmbeddingProviderInterface
from core.interfaces.llm_provider import LLMProviderInterface
from core.interfaces.vector_store import VectorStoreInterface


class ChatbotAgent(BaseAgent):
    """Q&A over uploaded docs. Not part of the latex graph."""

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

    def retrieve_context(self, query: str) -> List[Dict[str, Any]]:
        try:
            query_vector = self.embedding_provider.embed_text(query)
        except Exception as e:
            self.logger.error(f"Failed to embed query: {e}")
            return []

        results = []
        for collection in (self.config.TEXTBOOK_COLLECTION_NAME, self.config.SLIDES_COLLECTION_NAME):
            if not collection:
                continue
            try:
                results.extend(self.vector_store.search(collection, query_vector, limit=10))
            except Exception as e:
                self.logger.warning(f"Retrieval warning for {collection}: {e}")

        seen = set()
        unique = []
        for doc in results:
            text = doc.get("payload", {}).get("text", "")
            if text and text not in seen:
                unique.append(doc)
                seen.add(text)
        return unique

    def build_context_string(self, retrieved_docs: List[Dict[str, Any]]) -> str:
        if not retrieved_docs:
            return ""
        parts = []
        for i, doc in enumerate(retrieved_docs, 1):
            meta = doc.get("payload", {})
            header = f"[Source {i}: {meta.get('source_file', 'unknown')}, page {meta.get('page', '?')}]"
            heading = meta.get("heading", "")
            if heading and heading != "Unknown":
                header += f" ({heading})"
            parts.append(f"{header}\n {meta.get('text', '')}")
        return "\n\n---\n\n".join(parts)

    def __call__(
        self,
        user_message: str,
        chat_history: List[Dict[str, str]],
        session_summary: str,
    ) -> Dict[str, Any]:
        retrieved = self.retrieve_context(user_message)
        context = self.build_context_string(retrieved)

        system_parts = [
            "You are a helpful study assistant who helps students understand their course material by answering questions clearly and accurately",
            "Guidelines:",
            "- Answer based on the provided document context when available",
            "- If referencing specific information, mention the source (example: according to this part of page i...)",
            "- If no document context available, answer from your general knowledge and mention that no uploaded documents were found",
            "- Be concise but thorough",
            "- Use examples for concepts you feel are difficult to understand",
            "- If you are unsure, say that you are unsure rather than guessing",
        ]
        if session_summary:
            system_parts.extend(["", "PREVIOUS CONVERSATION SUMMARY:", session_summary])
        if context:
            system_parts.extend(["", "RELEVANT CONTEXT FROM UPLOADED DOCUMENTS:", context])
        else:
            system_parts.extend(["", "NO RELEVANT DOCUMENTS WERE FOUND, ANSWER FROM YOUR GENERAL KNOWLEDGE"])

        messages = [{"role": "system", "content": "\n".join(system_parts)}]
        for msg in chat_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})

        try:
            answer = self.llm.invoke(messages).content
        except Exception as e:
            self.logger.error(f"LLM generation failed: {e}", exc_info=True)
            answer = "The assistant is currently unavailable."

        sources = []
        for doc in retrieved:
            meta = doc.get("payload", {})
            sources.append(
                {
                    "source_file": meta.get("source_file", "Unknown"),
                    "page": meta.get("page"),
                    "heading": meta.get("heading"),
                    "score": doc.get("score"),
                }
            )
        return {"answer": answer, "sources": sources}
