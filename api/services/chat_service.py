import time
import uuid
from typing import Any, Dict, List

from sqlalchemy.orm import Session
from sqlalchemy import desc

from agents.chatbot.chatbot import ChatbotAgent
from core.config import Config
from core.interfaces.context_provider import ContextProviderInterface
from core.interfaces.chat_storage import ChatStorageInterface
from core.interfaces.embedding_provider import EmbeddingProviderInterface
from core.interfaces.llm_provider import LLMProviderInterface
from core.interfaces.vector_store import VectorStoreInterface
from db.models import ChatMessage, ChatSession


class HybridChatStorage(ChatStorageInterface):
    """Chat memory stored in PostgreSQL for exact history and Qdrant for semantic search."""

    def __init__(
        self,
        db_session: Session,
        config: Config,
        vector_store: VectorStoreInterface,
        embedding_provider: EmbeddingProviderInterface,
    ):
        self.db = db_session
        self.config = config
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider

    def save_message(self, user_id: int, session_id: str, role: str, message: str) -> None:
        msg_id = str(uuid.uuid4())
        timestamp = int(time.time())
        
        # 1. Save to Postgres
        sql_msg = ChatMessage(
            id=msg_id,
            session_id=session_id,
            user_id=user_id,
            role=role,
            content=message,
            timestamp=timestamp,
            is_summarized=0
        )
        self.db.add(sql_msg)
        self.db.commit()

        # 2. Save to Qdrant for semantic capabilities
        point = {
            "id": msg_id,
            "vector": [0.0] * self.config.VECTOR_SIZE, # Placeholder if no sync embedding is done, but typically we would embed here
            "payload": {
                "user_id": user_id,
                "session_id": session_id,
                "role": role,
                "message": message,
                "timestamp": timestamp,
                "is_summarized": False,
            },
        }
        self.vector_store.upsert(self.config.MEMORY_COLLECTION_NAME, [point])

    def get_messages(self, user_id: int, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        # Fetch from Postgres (Chronological)
        messages = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id, ChatMessage.user_id == user_id, ChatMessage.is_summarized == 0)
            .order_by(ChatMessage.timestamp.asc())
            .limit(limit)
            .all()
        )
        
        return [
            {
                "id": m.id,
                "payload": {
                    "role": m.role,
                    "message": m.content,
                    "timestamp": m.timestamp,
                    "is_summarized": bool(m.is_summarized)
                }
            }
            for m in messages
        ]

    def get_summary(self, user_id: int, session_id: str) -> str:
        session_obj = (
            self.db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .first()
        )
        if session_obj and session_obj.summary:
            return session_obj.summary
        return ""

    def update_summary(self, user_id: int, session_id: str, new_summary: str, summarized_message_ids: List[str]) -> None:
        # Update Postgres summary
        session_obj = (
            self.db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .first()
        )
        if session_obj:
            session_obj.summary = new_summary

        # Mark Postgres messages as summarized
        if summarized_message_ids:
            self.db.query(ChatMessage).filter(ChatMessage.id.in_(summarized_message_ids)).update(
                {"is_summarized": 1}, synchronize_session=False
            )
        self.db.commit()

        # Mark Qdrant messages as summarized (Optional but good for consistency)
        if hasattr(self.vector_store, "client"):
            for rec_id in summarized_message_ids:
                self.vector_store.client.set_payload(
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
