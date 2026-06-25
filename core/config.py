from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Config(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_TEMPERATURE: float = 0.0
    TEXTBOOK_COLLECTION_NAME: str = ""
    SLIDES_COLLECTION_NAME: str = ""
    MEMORY_COLLECTION_NAME: str = "chat_memory"
    VECTOR_SIZE: int = 384
    EMBEDDING_MODEL: str = "BAAI/bge-small-en"
    UPLOADS_DIR: str = "/uploads"

    # Postgres
    POSTGRES_URI: str = "sqlite:///./dummy.db"

    # Qdrant
    QDRANT_PATH: str = "qdrant"
    QDRANT_PORT: int = 6333

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_SOCKET_CONNECT_TIMEOUT: float = 5.0
    REDIS_SOCKET_TIMEOUT: float = 15.0

    # JWT Auth
    SECRET_KEY: str = "super_secret_key_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


config = Config()
