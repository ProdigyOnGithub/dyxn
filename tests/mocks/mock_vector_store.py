from typing import Any, Dict, List, Optional

from core.interfaces.vector_store import VectorStoreInterface


class MockVectorStore(VectorStoreInterface):
    def __init__(self):
        self.collections = {}

    def ensure_collection(self, collection_name: str) -> None:
        self.collections.setdefault(collection_name, {})

    def upsert(self, collection_name: str, points: List[Dict[str, Any]]) -> None:
        self.ensure_collection(collection_name)
        for point in points:
            self.collections[collection_name][point["id"]] = point

    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 5,
        query_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        self.ensure_collection(collection_name)
        out = []
        for i, (point_id, point) in enumerate(self.collections[collection_name].items()):
            if i >= limit:
                break
            out.append({"id": point_id, "score": 0.99, "payload": point.get("payload", {})})
        return out

    def delete(self, collection_name: str, point_ids: List[str]) -> None:
        bucket = self.collections.get(collection_name, {})
        for pid in point_ids:
            bucket.pop(pid, None)
