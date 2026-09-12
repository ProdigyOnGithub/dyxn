import time
import uuid
from typing import Any, Dict

from agents.chatbot import ChatbotAgent
from core.config import Config
from core.interfaces.context_provider import ContextProviderInterface
from core.interfaces.embedding_provider import EmbeddingProviderInterface
from core.interfaces.llm_provider import LLMProviderInterface
from core.interfaces.vector_store import VectorStoreInterface


class QdrantContextManager(ContextProviderInterface):
    """Chat memory in Qdrant. Uses scroll on the raw client because the
    vector-store interface doesn't have a filter/scroll method yet."""

    def __init__(
        self,
        config: Config,
        vector_store: VectorStoreInterface,
        embedding_provider: EmbeddingProviderInterface,
        llm: LLMProviderInterface,
    ):
        self.config = config
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.llm = llm

    def save_message(self, user_id: int, session_id: str, role: str, message: str) -> None:
        point = {
            "id": str(uuid.uuid4()),
            "vector": [0.0] * self.config.VECTOR_SIZE,
            "payload": {
                "user_id": user_id,
                "session_id": session_id,
                "role": role,
                "message": message,
                "timestamp": time.time(),
                "is_summarized": False,
            },
        }
        self.vector_store.upsert(self.config.MEMORY_COLLECTION_NAME, [point])

    def _scroll(self, must: list, must_not: list | None = None, limit: int = 20):
        if not hasattr(self.vector_store, "client"):
            return []
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        conditions = [
            FieldCondition(key=k, match=MatchValue(value=v)) for k, v in must
        ]
        exclude = [
            FieldCondition(key=k, match=MatchValue(value=v)) for k, v in (must_not or [])
        ]
        records, _ = self.vector_store.client.scroll(
            collection_name=self.config.MEMORY_COLLECTION_NAME,
            scroll_filter=Filter(must=conditions, must_not=exclude or None),
            limit=limit,
        )
        return records

    def get_context(self, user_id: int, session_id: str, window_size: int = 5) -> Dict[str, Any]:
        if not hasattr(self.vector_store, "client"):
            return {"summary": "", "recent_messages": []}

        summary_records = self._scroll(
            must=[("session_id", session_id), ("user_id", user_id), ("role", "system_summary")],
            limit=1,
        )
        summary = summary_records[0].payload.get("message", "") if summary_records else ""

        records = self._scroll(
            must=[("session_id", session_id), ("user_id", user_id), ("is_summarized", False)],
            must_not=[("role", "system_summary")],
            limit=20,
        )
        recent = sorted(records, key=lambda r: r.payload.get("timestamp", 0))[-window_size:]
        messages = [{"role": r.payload["role"], "content": r.payload["message"]} for r in recent]
        return {"summary": summary, "recent_messages": messages}

    def summarize(self, user_id: int, session_id: str, window_size: int = 5) -> None:
        if not hasattr(self.vector_store, "client"):
            return

        records = self._scroll(
            must=[("session_id", session_id), ("user_id", user_id), ("is_summarized", False)],
            must_not=[("role", "system_summary")],
            limit=50,
        )
        sorted_records = sorted(records, key=lambda r: r.payload.get("timestamp", 0))
        if len(sorted_records) <= window_size:
            return

        to_summarize = sorted_records[:-window_size]
        summary_records = self._scroll(
            must=[("session_id", session_id), ("user_id", user_id), ("role", "system_summary")],
            limit=1,
        )
        existing = summary_records[0].payload.get("message", "") if summary_records else ""
        messages_text = "\n".join(f'{r.payload["role"]}: {r.payload["message"]}' for r in to_summarize)

        new_summary = self.llm.invoke(
            f"Summarize conversation. Previous: {existing}. New: {messages_text}"
        ).content.strip()

        if summary_records:
            self.vector_store.delete(self.config.MEMORY_COLLECTION_NAME, [summary_records[0].id])

        self.vector_store.upsert(
            self.config.MEMORY_COLLECTION_NAME,
            [
                {
                    "id": str(uuid.uuid4()),
                    "vector": self.embedding_provider.embed_text(new_summary),
                    "payload": {
                        "user_id": user_id,
                        "session_id": session_id,
                        "role": "system_summary",
                        "message": new_summary,
                        "timestamp": time.time(),
                        "is_summarized": False,
                    },
                }
            ],
        )

        client = self.vector_store.client
        for record in to_summarize:
            payload = record.payload.copy()
            payload["is_summarized"] = True
            client.set_payload(
                collection_name=self.config.MEMORY_COLLECTION_NAME,
                payload=payload,
                points=[record.id],
            )


class ChatService:
    def __init__(self, context_provider: ContextProviderInterface, chatbot: ChatbotAgent):
        self.context_provider = context_provider
        self.chatbot = chatbot

    def handle_chat(self, user_id: int, session_id: str, message: str) -> Dict[str, Any]:
        self.context_provider.save_message(user_id, session_id, "user", message)
        context = self.context_provider.get_context(user_id, session_id, window_size=5)

        try:
            result = self.chatbot(
                user_message=message,
                chat_history=context["recent_messages"],
                session_summary=context["summary"],
            )
            reply = result["answer"]
            sources = result.get("sources", [])
        except Exception:
            reply = "Error while processing question."
            sources = []

        self.context_provider.save_message(user_id, session_id, "ai", reply)
        return {"response": reply, "sources": sources}
