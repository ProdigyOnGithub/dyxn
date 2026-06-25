from contextlib import asynccontextmanager
import json
import logging
import time
import uuid
from pathlib import Path

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from api.auth import (
    check_ip_banned,
    create_access_token,
    get_password_hash,
    record_failed_attempt,
    reset_failed_attempts,
    verify_password,
)
from api.memory import (
    get_context_for_inference,
    initialize_memory_store,
    save_message,
    summarize_old_messages,
)
from core.config import config
from core.document_status import (
    create_document_status,
    get_document_status,
    list_document_statuses,
    mark_document_failed,
)
from core.redis import redis_client
from db.models import Base, User
from db.postgres import engine, get_db
from schemas import ChatMessage, Token, UserCreate


logger = logging.getLogger(__name__)

ALLOWED_DOCUMENT_SOURCE_TYPES = {"textbook", "slides"}
STARTUP_RETRIES = 12
STARTUP_RETRY_DELAY_SECONDS = 5
UI_DIR = Path(__file__).resolve().parent.parent / "ui"


def initialize_runtime_dependencies():
    last_error = None

    for attempt in range(1, STARTUP_RETRIES + 1):
        try:
            Base.metadata.create_all(bind=engine)
            initialize_memory_store()
            logger.info("Runtime dependencies initialized")
            return
        except Exception as exc:
            last_error = exc
            logger.exception(
                "Runtime dependency initialization failed attempt=%s/%s; retrying in %ss",
                attempt,
                STARTUP_RETRIES,
                STARTUP_RETRY_DELAY_SECONDS,
            )
            time.sleep(STARTUP_RETRY_DELAY_SECONDS)

    raise RuntimeError("Runtime dependencies did not become ready") from last_error


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_runtime_dependencies()
    yield


app = FastAPI(title="DYXN AI Backend", lifespan=lifespan)
app.mount("/assets", StaticFiles(directory=UI_DIR), name="ui-assets")


@app.get("/", include_in_schema=False)
def serve_ui():
    return FileResponse(UI_DIR / "index.html")


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
    except Exception:
        db.rollback()
        logger.exception("Database error during registration username=%s", user.username)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during registration",
        )


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
async def upload_document(
    file: UploadFile = File(...),
    source_type: str = Form("textbook"),
    current_user: User = Depends(get_current_user),
):
    uploads_dir = Path(config.UPLOADS_DIR)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided")

    normalized_source_type = source_type.strip().lower()
    if normalized_source_type not in ALLOWED_DOCUMENT_SOURCE_TYPES:
        allowed = ", ".join(sorted(ALLOWED_DOCUMENT_SOURCE_TYPES))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid source_type. Expected one of: {allowed}",
        )

    document_id = uuid.uuid4().hex
    safe_filename = file.filename.replace("/", "_").replace("\\", "_")
    destination_path = uploads_dir / f"{document_id}_{safe_filename}"

    try:
        with open(destination_path, "wb") as out_file:
            while chunk := await file.read(1024 * 1024):
                out_file.write(chunk)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {exc}",
        )

    create_document_status(
        current_user.id,
        document_id,
        safe_filename,
        normalized_source_type,
    )

    queued_payload = {
        "document_id": document_id,
        "owner_id": current_user.id,
        "filename": safe_filename,
        "path": str(destination_path),
        "source_type": normalized_source_type,
    }

    try:
        redis_client.xadd(
            "document_ingestion",
            {"data": json.dumps(queued_payload)},
        )
    except Exception as exc:
        mark_document_failed(current_user.id, document_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue document: {exc}",
        )

    return {
        "document_id": document_id,
        "filename": safe_filename,
        "source_type": normalized_source_type,
        "status": "queued",
    }


@app.get("/documents/status")
def document_statuses(current_user: User = Depends(get_current_user)):
    return {"documents": list_document_statuses(current_user.id)}


@app.get("/documents/{document_id}/status")
def document_status(document_id: str, current_user: User = Depends(get_current_user)):
    document = get_document_status(current_user.id, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@app.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session(current_user: User = Depends(get_current_user)):
    session_id = str(uuid.uuid4())
    return {"id": session_id, "title": "New Chat"}


@app.post("/sessions/{session_id}/chat")
def chat(
    session_id: str,
    chat_message: ChatMessage,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    save_message(current_user.id, session_id, "user", chat_message.message)
    context = get_context_for_inference(current_user.id, session_id, window_size=5)

    try:
        from graph import graph

        initial_state = {
            "owner_id": current_user.id,
            "syllabus_topic": chat_message.message,
            "document_statuses": list_document_statuses(current_user.id),
            "chat_history": context["recent_messages"],
            "session_summary": context["summary"],
            "retrieved_chunks": [],
            "retrieved_metadata": [],
            "retrieval_ready": False,
            "retrieval_warnings": [],
            "generation_blocked": False,
            "blocked_reason": "",
            "working_notes": "",
            "synthesized_section": "",
            "latex_output": "",
            "evaluation_score": 0.0,
            "evaluation_feedback": [],
            "evaluation_iterations": 0,
        }
        result = graph.invoke(initial_state)
        ai_response = result.get("latex_output", "")
        if not ai_response:
            ai_response = "I encountered an error generating notes."
    except Exception:
        logger.exception("Graph execution error session_id=%s user_id=%s", session_id, current_user.id)
        ai_response = "I encountered an internal error generating notes. Please try again later."

    save_message(current_user.id, session_id, "ai", ai_response)
    background_tasks.add_task(summarize_old_messages, current_user.id, session_id, 5)

    return {"response": ai_response}
