import json
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from core.redis import redis_client
from api.services.auth_service import AuthService
from db.models import User
from fastapi import Depends

router = APIRouter(dependencies=[Depends(AuthService.get_current_user)])


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...), current_user: User = Depends(AuthService.get_current_user)):
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided")

    document_id = uuid.uuid4().hex
    safe_filename = file.filename.replace("/", "_").replace("\\", "_")
    destination_path = uploads_dir / f"{document_id}_{safe_filename}"

    try:
        with open(destination_path, "wb") as out_file:
            while chunk := await file.read(1024 * 1024):
                out_file.write(chunk)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {e}",
        )

    from api.services.progress_manager import DocumentProgressManager
    progress = DocumentProgressManager()
    progress.create(document_id, current_user.id, str(destination_path))

    redis_client.xadd(
        "document_processing",
        {
            "data": json.dumps(
                {
                    "document_id": document_id,
                    "owner_id": current_user.id,
                    "filename": safe_filename,
                    "path": str(destination_path),
                }
            )
        },
    )

    return {
        "document_id": document_id,
        "filename": safe_filename,
        "status": "queued",
    }

from fastapi import WebSocket, WebSocketDisconnect
from api.services.websocket_manager import manager

@router.websocket("/ws/progress/{document_id}")
async def progress_socket(websocket: WebSocket, document_id: str):
    await manager.connect(websocket, document_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, document_id)
