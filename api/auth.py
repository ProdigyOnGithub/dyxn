from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Request
from core.config import config
from core.redis import redis_client

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt



MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def check_ip_banned(request: Request):
    ip = get_client_ip(request)
    if redis_client.exists(f"lockout:{ip}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again later."
        )

def record_failed_attempt(request: Request):
    ip = get_client_ip(request)
    attempts_key = f"attempts:{ip}"
    
    count = redis_client.incr(attempts_key)
    
    if count == 1:
        redis_client.expire(attempts_key, LOCKOUT_MINUTES * 60)
        
    if count >= MAX_FAILED_ATTEMPTS:
        redis_client.setex(f"lockout:{ip}", LOCKOUT_MINUTES * 60, "1")
        redis_client.delete(attempts_key)

def reset_failed_attempts(request: Request):
    ip = get_client_ip(request)
    redis_client.delete(f"attempts:{ip}")
    redis_client.delete(f"lockout:{ip}")
