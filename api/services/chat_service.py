import time
import uuid
from typing import Any, Dict, List

from agents.chatbot.chatbot import ChatbotAgent
from core.config import Config
from core.interfaces.context_provider import ContextProviderInterface
from core.interfaces.chat_storage import ChatStorageInterface
from core.interfaces.embedding_provider import EmbeddingProviderInterface
from core.interfaces.llm_provider import LLMProviderInterface
from core.interfaces.vector_store import VectorStoreInterface


class QdrantChatStorage(ChatStorageInterface):
    """Chat memory in Qdrant."""

    def __init__(
        self,
        config: Config,
        vector_store: VectorStoreInterface,
        embedding_provider: EmbeddingProviderInterface,
    ):
        self.config = config
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider

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

    def get_messages(self, user_id: int, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        records = self._scroll(
            must=[("session_id", session_id), ("user_id", user_id), ("is_summarized", False)],
            must_not=[("role", "system_summary")],
            limit=limit,
        )
        return [{"id": r.id, "payload": r.payload} for r in records]

    def get_summary(self, user_id: int, session_id: str) -> str:
        summary_records = self._scroll(
            must=[("session_id", session_id), ("user_id", user_id), ("role", "system_summary")],
            limit=1,
        )
        if summary_records:
            return summary_records[0].payload.get("message", "")
        return ""

    def update_summary(self, user_id: int, session_id: str, new_summary: str, summarized_message_ids: List[str]) -> None:
        if not hasattr(self.vector_store, "client"):
            return

        summary_records = self._scroll(
            must=[("session_id", session_id), ("user_id", user_id), ("role", "system_summary")],
            limit=1,
        )

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
        for rec_id in summarized_message_ids:
            client.set_payload(
                collection_name=self.config.MEMORY_COLLECTION_NAME,
                payload={"is_summarized": True},
                points=[rec_id],
            )


class SlidingWindowContextProvider(ContextProviderInterface):
    """Context provider that uses a sliding window of recent messages and a summary."""
    
    def __init__(self, chat_storage: ChatStorageInterface, llm: LLMProviderInterface):
        self.chat_storage = chat_storage
        self.llm = llm

    def get_context(self, user_id: int, session_id: str, window_size: int = 5, **kwargs) -> Dict[str, Any]:
        summary = self.chat_storage.get_summary(user_id, session_id)
        messages_records = self.chat_storage.get_messages(user_id, session_id, limit=20)
        
        # Sort by timestamp
        recent = sorted(messages_records, key=lambda r: r["payload"].get("timestamp", 0))[-window_size:]
        messages = [{"role": r["payload"]["role"], "content": r["payload"]["message"]} for r in recent]
        
        return {"summary": summary, "recent_messages": messages}

    def summarize(self, user_id: int, session_id: str, window_size: int = 5) -> None:
        records = self.chat_storage.get_messages(user_id, session_id, limit=50)
        sorted_records = sorted(records, key=lambda r: r["payload"].get("timestamp", 0))
        
        if len(sorted_records) <= window_size:
            return

        to_summarize = sorted_records[:-window_size]
        existing_summary = self.chat_storage.get_summary(user_id, session_id)
        
        messages_text = "\n".join(f'{r["payload"]["role"]}: {r["payload"]["message"]}' for r in to_summarize)
        
        new_summary = self.llm.invoke(
            f"Summarize conversation. Previous: {existing_summary}. New: {messages_text}"
        ).content.strip()

        summarized_ids = [r["id"] for r in to_summarize]
        self.chat_storage.update_summary(user_id, session_id, new_summary, summarized_ids)


class ChatService:
    def __init__(self, chat_storage: ChatStorageInterface, context_provider: ContextProviderInterface, chatbot: ChatbotAgent):
        self.chat_storage = chat_storage
        self.context_provider = context_provider
        self.chatbot = chatbot

    def handle_chat(self, user_id: int, session_id: str, message: str) -> Dict[str, Any]:
        self.chat_storage.save_message(user_id, session_id, "user", message)
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

        self.chat_storage.save_message(user_id, session_id, "ai", reply)
        return {"response": reply, "sources": sources}
