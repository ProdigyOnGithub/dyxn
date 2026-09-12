from abc import ABC, abstractmethod
from typing import Any, Dict


class ContextProviderInterface(ABC):
    @abstractmethod
    def get_context(self, user_id: int, session_id: str, **kwargs) -> Dict[str, Any]:
        """
        Retrieves context for the LLM. 
        Implementations could be SlidingWindowContextProvider, RetrievalContextProvider, etc.
        Returns a dictionary, e.g., {"summary": "...", "recent_messages": [{"role": "...", "content": "..."}, ...]}
        """
        pass
