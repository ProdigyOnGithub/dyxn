from retrieval.retriever import Retriever
from db.qdrant import client
from core.config import config
from core.llm import get_llm
from ingestion.embedding import embed_text
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import logging

logger = logging.getLogger(__name__)
llm = get_llm()

tb_retriever = None
if config.TEXTBOOK_COLLECTION_NAME:
    tb_retriever = Retriever(client, config.TEXTBOOK_COLLECTION_NAME,embed_text)
sl_retriever = None
if config.SLIDES_COLLECTION_NAME:
    sl_retriever = Retriever(client, config.SLIDES_COLLECTION_NAME,embed_text)

def retrieve_context(query: str)-> list[dict]: # uh searches qdrant for tb and slides returns unique unduplicated results
    results = []
    if tb_retriever:
        try:
            results.extend(tb_retriever.retrieve(query,limit=10))
        except Exception as E:
            logger.warning(f"Tb retriver L: {E}")
    
    if sl_retriever:
        try:
            results.extend(sl_retriever.retrieve(query,limit=10))
        except Exception as E:
            logger.warning(f"slides retriver L: {E}")
    
    saw=set()
    unique=[]
    for doc in results:
        text =doc["text"]
        if text not in saw:
            unique.append(doc)
            saw.add(text)
    return unique

def build_context(retrieved_docs: list[dict]) -> str: # makes the retrieved chunks into a string for llm, includes metadata if there sometimes
    if not retrieved_docs:
        return ""
    context_parts = []
    for i,doc in enumerate(retrieved_docs,1):
        metad = doc.get("metadata",{})
        source_file = metad.get("source_file","unknown")
        page = metad.get("page","?")
        heading = metad.get("heading","")
        header = f"[Source {i}:{source_file},page {page}]"
        if heading and heading!="Unknown":
            header+= f"({heading})"
        context_parts.append(f"{header}\n {doc['text']}")
    return "\n\n---\n\n".join(context_parts) 

def chatbot_agent(user_message: str, chat_history: list[dict],session_summary: str)->dict:
    retrieved_docs=retrieve_context(user_message)
    context=build_context(retrieved_docs)
    system_parts = [
        "you are a helpful study assistant who helps students understand their course material by answering questions clearly and accurately",
        "guidelines:",
        "-answer based on the provided document context when available",
        "-if referencing specific information, mentionthe source(example: according to this part of page i...)",
        "-if no document context available, answer from your general knowledge to the best of your knowledge and mentino that no uploaded documents were for found for this generation",
        "-be consice but also be thorough",
        "- use examples for concepts which you feel are difficult to understand",
        "- if you are unsure, say that you are unsure of this thing rather than guessing things and beating around the bush",
    ]

    if session_summary:
        system_parts.append("")
        system_parts.append("PREVIOUS CONVERSATION SUMMARY:")
        system_parts.append(session_summary)

    if context:
        system_parts.append("")
        system_parts.append(" RELEVANT CONTEXT FROM UPLOADED DOCUMENTS:")
        system_parts.append(context)
    else:
        system_parts.append("")
        system_parts.append("NO RELEVANT DOCUMENTS WERE FOUND, ANSWER FROM YOUR GENERAL KNOWLEDGE")

    system_prompt="\n".join(system_parts)
    
    messages = [SystemMessage(content=system_prompt)]

    for msg in chat_history:
        role = msg["role"]
        content = msg["content"]

        if role =="user":
            messages.append(HumanMessage(content=content))
        elif role == "ai":
            messages.append(AIMessage(content=content))
    messages.append(HumanMessage(content=user_message))

    try:
        response = llm.invoke(messages)
        answer=response.content
    except Exception as E:
        logger.error(f"llm dont want to talk:{E}",exc_info=True)
        answer = "llm dont want to respond check logs for more info"
    
    sources = []
    for doc in retrieved_docs:
        meta = doc.get("metadata",{})
        sources.append(
            {
                "source_file":meta.get("source_file","Unknown"),
                "page":meta.get("page"),
                "heading":meta.get("heading"),
                "score":doc.get("score"),
            }
        )
    return {
        "answer":answer, "sources":sources
    }