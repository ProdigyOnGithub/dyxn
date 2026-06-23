from fastapi import FastAPI, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from jose import JWTError, jwt
from typing import List
import uuid

from schemas import UserCreate, Token, ChatMessage

from core.config import config
from db.postgres import engine, get_db
from db.models import Base, User
from api.auth import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    check_ip_banned, 
    record_failed_attempt, 
    reset_failed_attempts
)
from api.memory import get_context_for_inference, save_message, summarize_old_messages


Base.metadata.create_all(bind=engine)

app = FastAPI(title="DYXN AI Backend")



oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(username=user.username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully"}


@app.post("/login", response_model=Token)
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    check_ip_banned(request)
    
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        record_failed_attempt(request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    reset_failed_attempts(request)
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session(current_user: User = Depends(get_current_user)):
    """Creates a new AI chat session ID."""
    session_id = str(uuid.uuid4())
    return {"id": session_id, "title": "New Chat"}


@app.post("/sessions/{session_id}/chat")
def chat(session_id: str, chat_message: ChatMessage, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user)):
    """
    Sends a message to a specific session.
    Invokes the original LangGraph pipeline with the context from Qdrant.
    """

    save_message(current_user.id, session_id, "user", chat_message.message)
    
    
    context = get_context_for_inference(current_user.id, session_id, window_size=5)
    
    try:
        from graph import graph
        initial_state = {
            "syllabus_topic": chat_message.message,
            "chat_history": context["recent_messages"],
            "session_summary": context["summary"],
            "retrieved_chunks": [],
            "retrieved_metadata": [],
            "working_notes": "",
            "synthesized_section": "",
            "latex_output": "",
            "evaluation_score": 0.0,
            "evaluation_feedback": []
        }
        result = graph.invoke(initial_state)
        ai_response = result.get("latex_output", "")
        if not ai_response:
             ai_response = "I encountered an error generating notes."
    except Exception as e:
        ai_response = f"Graph execution error: {e}"
        
  
    save_message(current_user.id, session_id, "ai", ai_response)
    
    
    background_tasks.add_task(summarize_old_messages, current_user.id, session_id, 5)
    
    return {"response": ai_response}
