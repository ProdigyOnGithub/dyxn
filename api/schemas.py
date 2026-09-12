from typing import Optional

from pydantic import BaseModel


class EvalOutput(BaseModel):
    score: float
    feedback: list[str]


class UserCreate(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class ChatMessage(BaseModel):
    message: str


class DocumentUploadRequest(BaseModel):
    url: str
    filename: Optional[str] = None
