from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Request
from core.config import config

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


failed_attempts: Dict[str, dict] = {}

def check_ip_banned(request: Request):
    ip = request.client.host if request.client else "unknown"
    if ip in failed_attempts:
        record = failed_attempts[ip]
        if record["locked_until"] and datetime.now(timezone.utc) < record["locked_until"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts. Try again later."
            )
        elif record["locked_until"] and datetime.now(timezone.utc) >= record["locked_until"]:
            
            failed_attempts[ip] = {"count": 0, "locked_until": None}

def record_failed_attempt(request: Request):
    ip = request.client.host if request.client else "unknown"
    if ip not in failed_attempts:
        failed_attempts[ip] = {"count": 0, "locked_until": None}
    
    failed_attempts[ip]["count"] += 1
    if failed_attempts[ip]["count"] >= MAX_FAILED_ATTEMPTS:
        failed_attempts[ip]["locked_until"] = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
        
def reset_failed_attempts(request: Request):
    ip = request.client.host if request.client else "unknown"
    if ip in failed_attempts:
        failed_attempts[ip] = {"count": 0, "locked_until": None}
