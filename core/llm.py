from langchain_groq import ChatGroq

from core.config import config


def get_llm():
    if not config.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is required to initialize the Groq chat model.")

    return ChatGroq(
        model=config.GROQ_MODEL,
        groq_api_key=config.GROQ_API_KEY,
        temperature=config.GROQ_TEMPERATURE,
    )
