from abc import ABC, abstractmethod
from typing import Any, Dict


class ContextProviderInterface(ABC):
    @abstractmethod
    def save_message(self, user_id: int, session_id: str, role: str, message: str) -> None:
        pass

    @abstractmethod
    def get_context(self, user_id: int, session_id: str, window_size: int = 5) -> Dict[str, Any]:
        """{summary: str, recent_messages: [{role, content}, ...]}"""
        pass

    @abstractmethod
    def summarize(self, user_id: int, session_id: str, window_size: int = 5) -> None:
        pass
