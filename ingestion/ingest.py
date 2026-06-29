import json
from qdrant_client.models import PointStruct
from ingestion.embedding import embed_batch
from db.qdrant import client, create_textbook_collection, create_slides_collection
from core.config import config
import uuid
from typing import List, Dict


def ingest_tb_chunks(json_file):

    create_textbook_collection()

    with open(json_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    texts = [chunk["text"] for chunk in chunks]

    embeddings = embed_batch(texts)

    points = []

    for chunk, vector in zip(chunks, embeddings):

        points.append(
            PointStruct(
                id=uuid.uuid4(),
                vector=vector,
                payload={
                    "text":
                    chunk["text"]
                }
            )
        )

    client.upsert(
        collection_name=config.TEXTBOOK_COLLECTION_NAME,
        points=points
    )

    print(f"Inserted {len(points)} textbook chunks")

def ingest_slides_chunks(json_file):

    create_slides_collection()

    with open(json_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    texts = [chunk["text"] for chunk in chunks]

    embeddings = embed_batch(texts)

    points = []

    for chunk, vector in zip(chunks, embeddings):

        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "text":
                    chunk["text"]
                }
            )
        )

    client.upsert(
        collection_name=config.SLIDES_COLLECTION_NAME,
        points=points
    )

    print(f"Inserted {len(points)} slides chunks")

def upsert_chunk(chunk_id: str, embedding: List[float], payload: Dict):
    
    point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "chunk_id": chunk_id,
                    "owner_id": payload["owner_id"],
                    "document_id": payload["document_id"],
                    "chunk_index": payload["chunk_index"],
                    "text": payload["text"]
                }
            )
    collection_name = ""
    if payload["source_type"] == "textbook":
        collection_name = config.TEXTBOOK_COLLECTION_NAME
    elif payload["source_type"] == "slides":
        collection_name = config.SLIDES_COLLECTION_NAME
    else:
        return "Incorrect source type"
    
    client.upsert(
        collection_name=collection_name,
        points=[point]
    )


if __name__ == "__main__":

    ingest_tb_chunks("data/textbook_chunks.json")
    ingest_slides_chunks("data/slides_chunks.json")
    client.close()