from fastapi import HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from api.schemas import UserCreate
from core.config import config
from db.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def register_user(self, user_data: UserCreate) -> User:
        if self.db.query(User).filter(User.username == user_data.username).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

        user = User(
            username=user_data.username,
            hashed_password=self.get_password_hash(user_data.password),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate_user(self, username: str, password: str) -> User | None:
        user = self.db.query(User).filter(User.username == username).first()
        if not user or not self.verify_password(password, user.hashed_password):
            return None
        return user

    def create_access_token(self, data: dict) -> str:
        return jwt.encode(data, config.SECRET_KEY, algorithm=config.ALGORITHM)
