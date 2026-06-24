from pydantic import BaseModel
from typing import Optional

class EvalInput(BaseModel):
    model_name: str
    dataset_name: str
    num_samples: int

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