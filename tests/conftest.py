import sys
from unittest.mock import MagicMock

# Mock redis module and instance methods before any imports happen
mock_redis_lib = MagicMock()
mock_redis_instance = MagicMock()
# Prevent 429 Too Many Requests by returning False for exists
mock_redis_instance.exists.return_value = False
mock_redis_instance.incr.return_value = 1
mock_redis_lib.Redis.return_value = mock_redis_instance

sys.modules['redis'] = mock_redis_lib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.server import app
from db.postgres import get_db
from db.models import Base

# Setup a file-based SQLite database for testing to avoid connection-specific memory DB issues
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """
    Creates a fresh database schema on each test run and yields a session.
    Drops all tables after the test completes to ensure isolation.
    """
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    """
    Provides a FastAPI TestClient configured with a dependency override
    to use the testing SQLite database session instead of Postgres.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
