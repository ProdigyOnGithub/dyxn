from sentence_transformers import SentenceTransformer

from core.config import config


_MODEL = None


def _get_model():
    global _MODEL

    if _MODEL is None:
        _MODEL = SentenceTransformer(config.EMBEDDING_MODEL)

    return _MODEL


def embed_text(text: str):
    if not isinstance(text, str):
        raise TypeError(f"embed_text expected str, got {type(text).__name__}")

    embedding = _get_model().encode(
        text,
        normalize_embeddings=True,
    )

    return embedding.tolist()


def embed_batch(texts):
    if isinstance(texts, str):
        raise TypeError("embed_batch expected a list of strings, got str")

    embeddings = _get_model().encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    return embeddings.tolist()
