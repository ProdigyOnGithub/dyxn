from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
)

from core.config import config


client = QdrantClient(
    path=config.QDRANT_PATH
)


def create_textbook_collection():

    existing = [c.name for c in client.get_collections().collections]

    if config.TEXTBOOK_COLLECTION_NAME in existing:
        return

    client.create_collection(
        collection_name=config.TEXTBOOK_COLLECTION_NAME,

        vectors_config=VectorParams(
            size=config.VECTOR_SIZE,
            distance=Distance.COSINE
        )
    )

    print("Textbook Collection created")

def create_slides_collection():

    existing = [c.name for c in client.get_collections().collections]

    if config.SLIDES_COLLECTION_NAME in existing:
        return

    client.create_collection(
        collection_name=config.SLIDES_COLLECTION_NAME,

        vectors_config=VectorParams(
            size=config.VECTOR_SIZE,
            distance=Distance.COSINE
        )
    )

    print("Slides Collection created")