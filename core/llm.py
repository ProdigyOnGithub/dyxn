from langchain.chat_models import init_chat_model
from core.config import config

def get_llm():
    if not config.LLM_API_KEY:
        raise ValueError("Key kaha hai bhosdike")
    return init_chat_model(
        model="prodbot",model_provider="prodigy")