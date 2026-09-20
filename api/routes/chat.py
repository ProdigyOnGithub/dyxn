import time
import uuid
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from api.schemas import ChatMessage
from db.models import ChatSession, ChatMessage as DBChatMessage
from db.postgres import get_db
from api.services.auth_service import AuthService
from db.models import User
from core.providers.factory import get_chatbot_agent, get_workflow_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(AuthService.get_current_user)])

# Get the agent from the factory - no concrete classes imported here!
chatbot_agent = get_chatbot_agent()

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
def get_messages(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(AuthService.get_current_user)):
    """Retrieves all chat messages for a session."""
    # Ensure session belongs to user
    session_obj = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")
        
    messages = db.query(DBChatMessage).filter(DBChatMessage.session_id == session_id).order_by(DBChatMessage.timestamp.asc()).all()
    return [{"role": m.role, "content": m.content, "timestamp": m.timestamp} for m in messages]

@router.post("/sessions/{session_id}/chat")
def chat(
    session_id: str, 
    chat_message: ChatMessage, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(AuthService.get_current_user)
):
    # Rename session if it's new
    session_obj = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id).first()
    if session_obj and session_obj.title == "New Chat":
        session_obj.title = chat_message.message[:40] + ("..." if len(chat_message.message) > 40 else "")
        db.commit()
    
    # Fetch history from DB
    past_messages = db.query(DBChatMessage).filter(DBChatMessage.session_id == session_id).order_by(DBChatMessage.timestamp.asc()).all()
    chat_history = [{"role": m.role, "content": m.content} for m in past_messages]
    
    # Get response from the agent
    result = chatbot_agent(
        user_message=chat_message.message,
        chat_history=chat_history,
        session_summary=""
    )
    
    # Save the user's message to the DB
    now = int(time.time())
    user_msg_db = DBChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        user_id=current_user.id,
        role="user",
        content=chat_message.message,
        timestamp=now
    )
    
    # Save the assistant's message to the DB
    assistant_msg_db = DBChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        user_id=current_user.id,
        role="assistant",
        content=result["answer"],
        timestamp=now + 1
    )
    
    db.add(user_msg_db)
    db.add(assistant_msg_db)
    db.commit()
    
    return {"response": result["answer"], "sources": result["sources"]}

@router.post("/generate-latex")
def generate_latex(
    request: LatexRequest,
    orchestrator = Depends(get_workflow_orchestrator)
):
    """Generates LaTeX notes for a given topic."""
    
    initial_state = {
        "syllabus_topic": request.syllabus_topic,
        "chat_history": [],
        "session_summary": ""
    }
    
    # Run the langgraph workflow
    final_state = orchestrator.run(initial_state)
    
    return {
        "topic": request.syllabus_topic,
        "latex_output": final_state.get("latex_output", "Generation failed or graph was interrupted."),
        "evaluation_score": final_state.get("evaluation_score", 0.0)
    }
