from fastapi import FastAPI, Depends, HTTPException, status, Request, BackgroundTasks, File, UploadFile
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from jose import JWTError, jwt
from typing import List, Optional
import uuid
import logging
import os
import shutil
import json
from pathlib import Path
from urllib.parse import urlparse, unquote
import urllib.request

logger = logging.getLogger(__name__)

from schemas import UserCreate, Token, ChatMessage, DocumentUploadRequest

from core.config import config
from core.redis import redis_client
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
from task_queue.ingest import upload_doc
from agents.chatbot import chatbot_agent


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
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"message": "User created successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Database error during registration: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during registration")


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


@app.post("/documents/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    uploads_dir = Path("uploads")

    uploads_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided")

    document_id = uuid.uuid4().hex

    safe_filename = (
        file.filename
        .replace("/", "_")
        .replace("\\", "_")
    )

    destination_path = (
        uploads_dir /
        f"{document_id}_{safe_filename}"
    )

    try:

        with open(destination_path, "wb") as out_file:
            while chunk := await file.read(1024 * 1024):
                out_file.write(chunk)

    except Exception as e:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {e}"
        )

    redis_client.xadd(
        "document_processing",
        {
            "data": json.dumps(
                {
                    "document_id": document_id,
                    "owner_id": current_user.id,
                    "filename": safe_filename,
                    "path": str(destination_path)
                }
            )
        }
    )
    print(destination_path)
    id = upload_doc(document_id=document_id, path=str(destination_path), owner_id=current_user.id, source_type="textbook")

    return {
        "document_id": id,
        "filename": safe_filename,
        "status": "queued"
    }


@app.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session(current_user: User = Depends(get_current_user)):
    """Creates a new AI chat session ID."""
    session_id = str(uuid.uuid4())
    return {"id": session_id, "title": "New Chat"}

@app.post("/sessions/{session_id}/chat")
def chat(session_id:str, chat_message:ChatMessage,background_tasks:BackgroundTasks, current_user: User=Depends(get_current_user)):

    save_message(current_user.id, session_id,"user",chat_message.message)
    context = get_context_for_inference(current_user.id,session_id,window_size=5)

    try:
        result = chatbot_agent(
            user_message=chat_message.message,
            chat_history=context["recent_messages"],
            session_summary=context["summary"]
        )
        llm_response = result["answer"]
        sources = result.get("sources",[])
    except Exception as E:
        logger.error(f"error in session {session_id}:{E} from chatbot",exc_info=True)
        llm_response = "error while processing question"
        sources = []
    save_message(current_user.id, session_id,"ai",llm_response)
    background_tasks.add_task(summarize_old_messages,current_user.id,session_id,5)
    return {"response": llm_response,"sources" :sources}



