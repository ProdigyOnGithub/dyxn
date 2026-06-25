import logging

from core.config import config
from db.qdrant import client
from ingestion.embedding import embed_text
from qdrant_client.models import FieldCondition, Filter, MatchValue
from retrieval.retriever import Retriever

logger = logging.getLogger(__name__)

PROCESSING_STATUSES = {"queued", "chunking", "chunked", "embedding"}


tb_retriever = None
if config.TEXTBOOK_COLLECTION_NAME:
    tb_retriever = Retriever(client, config.TEXTBOOK_COLLECTION_NAME, embed_text)

sl_retriever = None
if config.SLIDES_COLLECTION_NAME:
    sl_retriever = Retriever(client, config.SLIDES_COLLECTION_NAME, embed_text)


def _existing_collections():
    return {collection.name for collection in client.get_collections().collections}


def _owner_filter(owner_id):
    if owner_id is None:
        return None

    return Filter(
        must=[
            FieldCondition(
                key="owner_id",
                match=MatchValue(value=owner_id),
            )
        ]
    )


def _retrieve_from_collection(retriever, collection_name, query, query_filter, warnings):
    if not retriever:
        return []

    try:
        return retriever.retrieve(query, limit=10, query_filter=query_filter)
    except Exception as e:
        warnings.append(f"Could not retrieve from {collection_name}: {e}")
        logger.error(
            "Retrieval failed for collection=%s query=%r. Error: %s",
            collection_name,
            query,
            e,
        )
        return []


def _document_status_warnings(document_statuses):
    warnings = []
    for document in document_statuses:
        status = document.get("status", "unknown")
        filename = document.get("filename", document.get("document_id", "document"))

        if status in PROCESSING_STATUSES:
            embedded = document.get("embedded_chunks", 0)
            total = document.get("total_chunks", 0)
            if total:
                warnings.append(
                    f"{filename} is still {status}: {embedded}/{total} chunks embedded."
                )
            else:
                warnings.append(f"{filename} is still {status}.")
        elif status == "failed":
            warnings.append(f"{filename} failed processing: {document.get('error', 'unknown error')}")

    return warnings


def retrieval_agent(state):
    query = state["syllabus_topic"]
    owner_id = state.get("owner_id")
    query_filter = _owner_filter(owner_id)
    document_statuses = state.get("document_statuses", [])

    results = []
    warnings = _document_status_warnings(document_statuses)

    try:
        existing = _existing_collections()
    except Exception as e:
        existing = set()
        warnings.append(f"Could not inspect Qdrant collections: {e}")
        logger.error("Could not inspect Qdrant collections. Error: %s", e)

    if tb_retriever:
        if config.TEXTBOOK_COLLECTION_NAME in existing:
            results.extend(
                _retrieve_from_collection(
                    tb_retriever,
                    config.TEXTBOOK_COLLECTION_NAME,
                    query,
                    query_filter,
                    warnings,
                )
            )
        else:
            warnings.append(f"Collection {config.TEXTBOOK_COLLECTION_NAME} does not exist yet.")

    if sl_retriever:
        if config.SLIDES_COLLECTION_NAME in existing:
            results.extend(
                _retrieve_from_collection(
                    sl_retriever,
                    config.SLIDES_COLLECTION_NAME,
                    query,
                    query_filter,
                    warnings,
                )
            )
        else:
            warnings.append(f"Collection {config.SLIDES_COLLECTION_NAME} does not exist yet.")

    seen = set()
    unique = []

    for doc in results:
        text = doc["text"]
        if text not in seen:
            unique.append(doc)
            seen.add(text)

    state["retrieved_chunks"] = [x["text"] for x in unique]
    state["retrieved_metadata"] = unique
    state["retrieval_ready"] = bool(unique)
    state["retrieval_warnings"] = warnings
    state["generation_blocked"] = not bool(unique)

    if not unique:
        processing_documents = [
            document for document in document_statuses
            if document.get("status") in PROCESSING_STATUSES
        ]
        failed_documents = [
            document for document in document_statuses
            if document.get("status") == "failed"
        ]

        if processing_documents:
            state["blocked_reason"] = (
                "The uploaded document is still processing, so there are no searchable "
                "chunks for it yet."
            )
        elif failed_documents:
            state["blocked_reason"] = "The uploaded document failed processing. Re-upload it or check worker logs."
        elif warnings:
            state["blocked_reason"] = "No source chunks were retrieved. The document may still be processing."
        else:
            state["blocked_reason"] = "No matching source chunks were found for this request."
    else:
        state["blocked_reason"] = ""

    return state
