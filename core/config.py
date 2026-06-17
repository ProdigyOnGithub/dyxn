from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Config(BaseSettings):
    OPENAI_API_KEY: str = ""
    COLLECTION_NAME: str = ""
    VECTOR_SIZE: int 
    QDRANT_PATH: str = ""


config = Config()