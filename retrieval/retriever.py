# retrieval/retriever.py

from qdrant_client import QdrantClient
from qdrant_client.models import Filter


class Retriever:

    def __init__(self, qdrant_client: QdrantClient, collection_name: str, embed_fn):
        self.client = qdrant_client
        self.collection_name = collection_name
        self.embed_fn = embed_fn

    def retrieve(self, query: str, limit: int = 5, query_filter: Filter | None = None) -> list[dict]:

        query_vector = self.embed_fn(query)

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
            query_filter=query_filter
        )

        documents = []

        for point in results.points:

            documents.append(
                {
                    "id": point.id,
                    "score": point.score,
                    "text": point.payload.get("text", ""),
                    "metadata": point.payload
                }
            )

        return documents