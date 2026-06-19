from sentence_transformers import SentenceTransformer

from core.config import config


model = SentenceTransformer(
    config.EMBEDDING_MODEL
)


def embed_text(text: str):

    embedding = model.encode(
        text,
        normalize_embeddings=True
    )

    return embedding.tolist()


def embed_batch(texts):

    embeddings = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    return embeddings.tolist()