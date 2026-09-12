from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class VectorStoreInterface(ABC):
    @abstractmethod
    def ensure_collection(self, collection_name: str) -> None:
        pass

    @abstractmethod
    def upsert(self, collection_name: str, points: List[Dict[str, Any]]) -> None:
        """Each point: {id, vector, payload}."""
        pass

    @abstractmethod
    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 5,
        query_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Hits look like {id, score, payload}."""
        pass

    @abstractmethod
    def delete(self, collection_name: str, point_ids: List[str]) -> None:
        pass
