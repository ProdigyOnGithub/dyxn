import logging
import time
import uuid

from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct

from core.config import config
from core.llm import get_llm
from db.qdrant import client, ensure_collection
from ingestion.embedding import embed_text


logger = logging.getLogger(__name__)
llm = None


def initialize_memory_store():
    ensure_collection(config.MEMORY_COLLECTION_NAME)


def get_memory_llm():
    global llm
    if llm is None:
        llm = get_llm()
    return llm


def save_message(user_id: int, session_id: str, role: str, message: str):
    initialize_memory_store()
    point = PointStruct(
        id=str(uuid.uuid4()),
        vector=[0.0] * config.VECTOR_SIZE,
        payload={
            "user_id": user_id,
            "session_id": session_id,
            "role": role,
            "message": message,
            "timestamp": time.time(),
            "is_summarized": False,
        },
    )
    client.upsert(collection_name=config.MEMORY_COLLECTION_NAME, points=[point])


def _session_filter(user_id: int, session_id: str, *extra_conditions):
    return Filter(
        must=[
            FieldCondition(key="session_id", match=MatchValue(value=session_id)),
            FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            *extra_conditions,
        ]
    )


def _system_summary_filter(user_id: int, session_id: str):
    return _session_filter(
        user_id,
        session_id,
        FieldCondition(key="role", match=MatchValue(value="system_summary")),
    )


def _unsummarized_filter(user_id: int, session_id: str):
    return Filter(
        must=[
            FieldCondition(key="session_id", match=MatchValue(value=session_id)),
            FieldCondition(key="user_id", match=MatchValue(value=user_id)),
            FieldCondition(key="is_summarized", match=MatchValue(value=False)),
        ],
        must_not=[
            FieldCondition(key="role", match=MatchValue(value="system_summary")),
        ],
    )


def _load_summary(user_id: int, session_id: str):
    summary_records, _ = client.scroll(
        collection_name=config.MEMORY_COLLECTION_NAME,
        scroll_filter=_system_summary_filter(user_id, session_id),
        limit=1,
    )
    if not summary_records:
        return "", []

    return summary_records[0].payload.get("message", ""), summary_records


def get_context_for_inference(user_id: int, session_id: str, window_size: int = 5):
    initialize_memory_store()

    summary, _ = _load_summary(user_id, session_id)
    records, _ = client.scroll(
        collection_name=config.MEMORY_COLLECTION_NAME,
        scroll_filter=_unsummarized_filter(user_id, session_id),
        limit=20,
    )

    sorted_records = sorted(records, key=lambda record: record.payload.get("timestamp", 0))
    recent_records = sorted_records[-window_size:]
    messages = [
        {"role": record.payload["role"], "content": record.payload["message"]}
        for record in recent_records
    ]

    return {
        "summary": summary,
        "recent_messages": messages,
    }


def summarize_old_messages(user_id: int, session_id: str, window_size: int = 5):
    initialize_memory_store()

    records, _ = client.scroll(
        collection_name=config.MEMORY_COLLECTION_NAME,
        scroll_filter=_unsummarized_filter(user_id, session_id),
        limit=50,
    )
    sorted_records = sorted(records, key=lambda record: record.payload.get("timestamp", 0))

    if len(sorted_records) <= window_size:
        return

    records_to_summarize = sorted_records[:-window_size]
    if not records_to_summarize:
        return

    existing_summary, summary_records = _load_summary(user_id, session_id)
    messages_text = "\n".join(
        f'{record.payload["role"]}: {record.payload["message"]}'
        for record in records_to_summarize
    )

    prompt = f"""You are summarizing a conversation for long-term memory.
Below is the previous summary (if any), followed by new messages.
Combine them into a single concise paragraph capturing key facts, topics discussed, and user intent.

PREVIOUS SUMMARY:
{existing_summary or 'None'}

NEW MESSAGES:
{messages_text}

NEW COMPREHENSIVE SUMMARY:"""

    try:
        response = get_memory_llm().invoke(prompt)
        new_summary = response.content.strip()

        if summary_records:
            client.delete(
                collection_name=config.MEMORY_COLLECTION_NAME,
                points_selector=[summary_records[0].id],
            )

        summary_point = PointStruct(
            id=str(uuid.uuid4()),
            vector=embed_text(new_summary),
            payload={
                "user_id": user_id,
                "session_id": session_id,
                "role": "system_summary",
                "message": new_summary,
                "timestamp": time.time(),
                "is_summarized": False,
            },
        )
        client.upsert(collection_name=config.MEMORY_COLLECTION_NAME, points=[summary_point])

        for record in records_to_summarize:
            updated_payload = record.payload.copy()
            updated_payload["is_summarized"] = True
            client.set_payload(
                collection_name=config.MEMORY_COLLECTION_NAME,
                payload=updated_payload,
                points=[record.id],
            )

        logger.info(
            "Session memory summarized session_id=%s messages=%s",
            session_id,
            len(records_to_summarize),
        )
    except Exception:
        logger.exception("Summarization failed session_id=%s", session_id)
