from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.config import config

engine = create_engine(
    config.POSTGRES_URI,
    connect_args={"check_same_thread": False} if config.POSTGRES_URI.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
