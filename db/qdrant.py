import logging

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from core.config import config


logger = logging.getLogger(__name__)
client = QdrantClient(
    host=config.QDRANT_PATH,
    port=config.QDRANT_PORT,
)

_ENSURED_COLLECTIONS = set()


def _extract_vector_size(collection_info):
    collection_config = getattr(collection_info, "config", None)
    params = getattr(collection_config, "params", None)
    vectors = getattr(params, "vectors", None)

    if hasattr(vectors, "size"):
        return vectors.size

    if isinstance(vectors, dict):
        if len(vectors) == 1:
            vector_config = next(iter(vectors.values()))
            return getattr(vector_config, "size", None)

        return {
            name: getattr(vector_config, "size", None)
            for name, vector_config in vectors.items()
        }

    return None


def _validate_collection_vector_size(collection_name: str):
    collection_info = client.get_collection(collection_name)
    vector_size = _extract_vector_size(collection_info)

    if vector_size is None:
        return

    if vector_size != config.VECTOR_SIZE:
        raise ValueError(
            f"Qdrant collection '{collection_name}' has vector size {vector_size}, "
            f"but config.VECTOR_SIZE is {config.VECTOR_SIZE}. Recreate the collection "
            "or align VECTOR_SIZE with EMBEDDING_MODEL."
        )


def ensure_collection(collection_name: str):
    if not collection_name:
        raise ValueError("Qdrant collection name is required")

    if collection_name in _ENSURED_COLLECTIONS:
        return

    existing = [c.name for c in client.get_collections().collections]

    if collection_name not in existing:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=config.VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
        )
        logger.info("Qdrant collection created collection=%s", collection_name)
    else:
        _validate_collection_vector_size(collection_name)

    _ENSURED_COLLECTIONS.add(collection_name)


def reset_collection_cache():
    _ENSURED_COLLECTIONS.clear()


def create_textbook_collection():
    ensure_collection(config.TEXTBOOK_COLLECTION_NAME)


def create_slides_collection():
    ensure_collection(config.SLIDES_COLLECTION_NAME)
