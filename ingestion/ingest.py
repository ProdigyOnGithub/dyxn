import json
import logging
import uuid
from typing import Dict, List

from qdrant_client.models import PointStruct

from core.config import config
from db.qdrant import client, ensure_collection
from ingestion.embedding import embed_batch


logger = logging.getLogger(__name__)

SOURCE_COLLECTIONS = {
    "textbook": "TEXTBOOK_COLLECTION_NAME",
    "slides": "SLIDES_COLLECTION_NAME",
}


def _collection_for_source_type(source_type: str) -> str:
    config_key = SOURCE_COLLECTIONS.get(source_type)
    if not config_key:
        allowed = ", ".join(sorted(SOURCE_COLLECTIONS))
        raise ValueError(f"Invalid source_type '{source_type}'. Expected one of: {allowed}")

    collection_name = getattr(config, config_key)
    if not collection_name:
        raise ValueError(f"{config_key} must be configured before ingesting {source_type} chunks")

    return collection_name


def _load_chunks(json_file):
    with open(json_file, "r", encoding="utf-8") as file:
        return json.load(file)


def _ingest_chunks(json_file, source_type):
    collection_name = _collection_for_source_type(source_type)
    ensure_collection(collection_name)

    chunks = _load_chunks(json_file)
    embeddings = embed_batch([chunk["text"] for chunk in chunks])
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={"text": chunk["text"]},
        )
        for chunk, vector in zip(chunks, embeddings)
    ]

    client.upsert(collection_name=collection_name, points=points)
    logger.info("Inserted chunks source_type=%s count=%s", source_type, len(points))


def ingest_tb_chunks(json_file):
    _ingest_chunks(json_file, "textbook")


def ingest_slides_chunks(json_file):
    _ingest_chunks(json_file, "slides")


def upsert_chunk(chunk_id: str, embedding: List[float], payload: Dict):
    collection_name = _collection_for_source_type(payload["source_type"])
    ensure_collection(collection_name)

    point_payload = {
        "chunk_id": chunk_id,
        "owner_id": payload["owner_id"],
        "document_id": payload["document_id"],
        "chunk_index": payload["chunk_index"],
        "source_type": payload["source_type"],
        "text": payload["text"],
    }

    for key in ("source_file", "page", "heading", "source_chunk_id"):
        if key in payload:
            point_payload[key] = payload[key]

    point = PointStruct(
        id=str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id)),
        vector=embedding,
        payload=point_payload,
    )
    client.upsert(collection_name=collection_name, points=[point])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ingest_tb_chunks("data/textbook_chunks.json")
    ingest_slides_chunks("data/slides_chunks.json")
    client.close()
