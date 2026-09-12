from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from core.config import Config
from core.interfaces.vector_store import VectorStoreInterface


class QdrantVectorStore(VectorStoreInterface):
    def __init__(self, config: Config):
        self.config = config
        self.client = QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT)

    def ensure_collection(self, collection_name: str) -> None:
        existing = [c.name for c in self.client.get_collections().collections]
        if collection_name in existing:
            return
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=self.config.VECTOR_SIZE, distance=Distance.COSINE),
        )

    def upsert(self, collection_name: str, points: List[Dict[str, Any]]) -> None:
        self.ensure_collection(collection_name)
        self.client.upsert(
            collection_name=collection_name,
            points=[
                PointStruct(id=p["id"], vector=p["vector"], payload=p.get("payload", {}))
                for p in points
            ],
        )

    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 5,
        query_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        self.ensure_collection(collection_name)
        # query_filter is unused — haven't mapped dicts onto Qdrant Filter yet
        results = self.client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=limit,
        )
        return [
            {"id": p.id, "score": p.score, "payload": p.payload}
            for p in results.points
        ]

    def delete(self, collection_name: str, point_ids: List[str]) -> None:
        self.client.delete(collection_name=collection_name, points_selector=point_ids)
