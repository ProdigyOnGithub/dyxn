import uuid

from fastapi import APIRouter, BackgroundTasks

from api.schemas import ChatMessage

router = APIRouter()


@router.post("/sessions", status_code=201)
def create_session():
    return {"id": str(uuid.uuid4()), "title": "New Chat"}


@router.post("/sessions/{session_id}/chat")
def chat(session_id: str, chat_message: ChatMessage, background_tasks: BackgroundTasks):
    # ChatService + ChatbotAgent are written, just not constructed here yet.
    # Need a real LLM and embedding provider first.
    _ = session_id, chat_message, background_tasks
    return {"response": "chat isn't wired up yet", "sources": []}
