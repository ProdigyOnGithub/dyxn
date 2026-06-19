from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Config(BaseSettings):
    OPENAI_API_KEY: str = ""
    TEXTBOOK_COLLECTION_NAME: str = ""
    SLIDES_COLLECTION_NAME: str = ""
    MEMORY_COLLECTION_NAME: str = "chat_memory"
    VECTOR_SIZE: int = 768
    QDRANT_PATH: str = ""
    EMBEDDING_MODEL: str = ""
    
    # Postgres
    POSTGRES_URI: str = "sqlite:///./dummy.db" 
    
    # JWT Auth
    SECRET_KEY: str = "super_secret_key_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


config = Config()