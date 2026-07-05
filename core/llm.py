from langchain.chat_models import init_chat_model
from core.config import config

def get_llm():
    if not config.GROQ_API_KEY:
        raise ValueError("Key kaha hai bhosdike")
    return init_chat_model(
        model="llama-3.3-70b-versatile",model_provider="groq")