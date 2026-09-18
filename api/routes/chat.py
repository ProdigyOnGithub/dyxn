import time
import uuid
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from api.schemas import ChatMessage
from db.models import ChatSession
from db.postgres import get_db
from api.services.auth_service import AuthService
from db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(AuthService.get_current_user)])

class LatexRequest(BaseModel):
    syllabus_topic: str

@router.post("/sessions", status_code=201)
def create_session(db: Session = Depends(get_db), current_user: User = Depends(AuthService.get_current_user)):
    """Creates a new AI chat session in the DB."""
    session_id = str(uuid.uuid4())
    new_session = ChatSession(
        id=session_id, 
        user_id=current_user.id, 
        title="New Chat", 
        created_at=int(time.time())
    )
    db.add(new_session)
    db.commit()
    return {"id": session_id, "title": "New Chat"}

@router.get("/sessions")
def list_sessions(db: Session = Depends(get_db), current_user: User = Depends(AuthService.get_current_user)):
    """Lists all chat sessions."""
    sessions = db.query(ChatSession).filter(ChatSession.user_id == current_user.id).order_by(ChatSession.created_at.desc()).all()
    return [{"id": s.id, "title": s.title} for s in sessions]

@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(AuthService.get_current_user)):
    """Deletes a chat session."""
    session_obj = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session_obj)
    db.commit()
    return {"message": "Session deleted successfully"}

@router.get("/sessions/{session_id}/messages")
def get_messages(session_id: str):
    """Retrieves all chat messages for a session (Mocked for now until ContextProvider is wired)."""
    return []

@router.post("/sessions/{session_id}/chat")
def chat(session_id: str, chat_message: ChatMessage, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(AuthService.get_current_user)):
    # Rename session if it's new
    session_obj = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id).first()
    if session_obj and session_obj.title == "New Chat":
        session_obj.title = chat_message.message[:40] + ("..." if len(chat_message.message) > 40 else "")
        db.commit()
        
    return {"response": "chat isn't wired up to the ChatbotAgent yet", "sources": []}

@router.post("/generate-latex")
def generate_latex(request: LatexRequest):
    """Generates LaTeX notes for a given topic."""
    from agents.latex.orchestrator import WorkflowOrchestrator
    
    # We would inject concrete LLM/Vector providers here in production
    # For now we'll just mock the orchestrator return or leave as stub
    
    return {
        "topic": request.syllabus_topic,
        "latex_output": "LaTeX generation is not fully wired yet.",
        "evaluation_score": 0.0
    }
