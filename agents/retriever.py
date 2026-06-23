from retrieval.retriever import Retriever
from db.qdrant import client
from core.config import config
from ingestion.embedding import embed_text
import logging

logger = logging.getLogger(__name__)


tb_retriever = None
if config.TEXTBOOK_COLLECTION_NAME:
    tb_retriever = Retriever(client, config.TEXTBOOK_COLLECTION_NAME, embed_text)

sl_retriever = None
if config.SLIDES_COLLECTION_NAME:
    sl_retriever = Retriever(client, config.SLIDES_COLLECTION_NAME, embed_text)

def retrieval_agent(state):

    query = state["syllabus_topic"]
    
    results = []
    
    if tb_retriever:
        try:
            results.extend(tb_retriever.retrieve(query, limit=10))
        except Exception as e:
            logger.error(f"Retrieval failed for collection={config.TEXTBOOK_COLLECTION_NAME} query='{query}'. Error: {e}")
            
    if sl_retriever:
        try:
            results.extend(sl_retriever.retrieve(query, limit=10))
        except Exception as e:
            logger.error(f"Retrieval failed for collection={config.SLIDES_COLLECTION_NAME} query='{query}'. Error: {e}")

    seen = set()
    unique = []

    for doc in results:

        text = doc["text"]

        if text not in seen:
            unique.append(doc)
            seen.add(text)

    state["retrieved_chunks"] = [x["text"] for x in unique]
    state["retrieved_metadata"] = unique

    return state