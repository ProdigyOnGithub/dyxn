from db.qdrant import client
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue, VectorParams, Distance
from core.config import config
from ingestion.embedding import embed_text
from core.llm import get_llm
import uuid
import time

# Ensure memory collection exists
try:
    client.get_collection(config.MEMORY_COLLECTION_NAME)
except Exception:
    client.create_collection(
        collection_name=config.MEMORY_COLLECTION_NAME,
        vectors_config=VectorParams(size=config.VECTOR_SIZE, distance=Distance.COSINE)
    )

llm = get_llm()

def save_message(user_id: int, session_id: str, role: str, message: str):
    """Saves a single message into Qdrant with a zero vector (no embedding needed for sequential chat)."""
    zero_vec = [0.0] * config.VECTOR_SIZE
    point = PointStruct(
        id=str(uuid.uuid4()),
        vector=zero_vec,
        payload={
            "user_id": user_id,
            "session_id": session_id,
            "role": role,
            "message": message,
            "timestamp": time.time(),
            "is_summarized": False
        }
    )
    client.upsert(collection_name=config.MEMORY_COLLECTION_NAME, points=[point])


def get_context_for_inference(user_id: int, session_id: str, window_size: int = 5):
    """
    Fetches the session summary (long-term memory) and last N messages (short-term memory).
    """
    
    summary = ""
    summary_records, _ = client.scroll(
        collection_name=config.MEMORY_COLLECTION_NAME,
        scroll_filter=Filter(
            must=[
                FieldCondition(key="session_id", match=MatchValue(value=session_id)),
                FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                FieldCondition(key="role", match=MatchValue(value="system_summary"))
            ]
        ),
        limit=1
    )
    if summary_records:
        summary = summary_records[0].payload.get("message", "")
    
    
    records, _ = client.scroll(
        collection_name=config.MEMORY_COLLECTION_NAME,
        scroll_filter=Filter(
            must=[
                FieldCondition(key="session_id", match=MatchValue(value=session_id)),
                FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                FieldCondition(key="is_summarized", match=MatchValue(value=False))
            ],
            must_not=[
                FieldCondition(key="role", match=MatchValue(value="system_summary"))
            ]
        ),
        limit=20  
    )
    
    sorted_records = sorted(records, key=lambda x: x.payload.get("timestamp", 0))
    recent = sorted_records[-window_size:]
    
    messages = [{"role": r.payload["role"], "content": r.payload["message"]} for r in recent]
    
    return {
        "summary": summary,
        "recent_messages": messages
    }


def summarize_old_messages(user_id: int, session_id: str, window_size: int = 5):
    """
    Background task: Summarizes older messages into a compressed summary stored in Qdrant.
    Only processes unsummarized messages outside the sliding window.
    """
    
    records, _ = client.scroll(
        collection_name=config.MEMORY_COLLECTION_NAME,
        scroll_filter=Filter(
            must=[
                FieldCondition(key="session_id", match=MatchValue(value=session_id)),
                FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                FieldCondition(key="is_summarized", match=MatchValue(value=False))
            ],
            must_not=[
                FieldCondition(key="role", match=MatchValue(value="system_summary"))
            ]
        ),
        limit=50 
    )
    
    sorted_records = sorted(records, key=lambda x: x.payload.get("timestamp", 0))
    
    if len(sorted_records) <= window_size:
        
        return
    
    
    to_summarize = sorted_records[:-window_size]
    
    if not to_summarize:
        return
    

    existing_summary = ""
    summary_records, _ = client.scroll(
        collection_name=config.MEMORY_COLLECTION_NAME,
        scroll_filter=Filter(
            must=[
                FieldCondition(key="session_id", match=MatchValue(value=session_id)),
                FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                FieldCondition(key="role", match=MatchValue(value="system_summary"))
            ]
        ),
        limit=1
    )
    if summary_records:
        existing_summary = summary_records[0].payload.get("message", "")
    
    
    messages_text = "\n".join([f'{r.payload["role"]}: {r.payload["message"]}' for r in to_summarize])
    
    prompt = f"""You are summarizing a conversation for long-term memory.
Below is the previous summary (if any), followed by new messages.
Combine them into a single concise paragraph capturing key facts, topics discussed, and user intent.

PREVIOUS SUMMARY:
{existing_summary or 'None'}

NEW MESSAGES:
{messages_text}

NEW COMPREHENSIVE SUMMARY:"""
    
    try:
        response = llm.invoke(prompt)
        new_summary = response.content.strip()
        
        
        if summary_records:
            client.delete(
                collection_name=config.MEMORY_COLLECTION_NAME,
                points_selector=[summary_records[0].id]
            )
        
        summary_vec = embed_text(new_summary)
        summary_point = PointStruct(
            id=str(uuid.uuid4()),
            vector=summary_vec,
            payload={
                "user_id": user_id,
                "session_id": session_id,
                "role": "system_summary",
                "message": new_summary,
                "timestamp": time.time(),
                "is_summarized": False
            }
        )
        client.upsert(collection_name=config.MEMORY_COLLECTION_NAME, points=[summary_point])
        
       
        for record in to_summarize:
            updated_payload = record.payload.copy()
            updated_payload["is_summarized"] = True
            client.set_payload(
                collection_name=config.MEMORY_COLLECTION_NAME,
                payload=updated_payload,
                points=[record.id]
            )
        
        print(f"Session {session_id} memory summarized. {len(to_summarize)} messages compressed.")
        
    except Exception as e:
        print(f"Summarization error for session {session_id}: {e}")
