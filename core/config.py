from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Config(BaseSettings):
    GROQ_API_KEY: str = ""
    TEXTBOOK_COLLECTION_NAME: str = ""
    SLIDES_COLLECTION_NAME: str = ""
    MEMORY_COLLECTION_NAME: str = "chat_memory"
    VECTOR_SIZE: int = 768
    EMBEDDING_MODEL: str = ""

    POSTGRES_URI: str = "sqlite:///./dummy.db"

    QDRANT_PATH: str = "./storage/qdrant"
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333

    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    # leftover from when login was required — unused while auth is off
    SECRET_KEY: str = "super_secret_key_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


config = Config()
