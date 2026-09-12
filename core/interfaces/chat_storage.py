from abc import ABC, abstractmethod
from typing import Any, Dict, List


class ChatStorageInterface(ABC):
    @abstractmethod
    def save_message(self, user_id: int, session_id: str, role: str, message: str) -> None:
        """Saves a single message to the chat history."""
        pass

    @abstractmethod
    def get_messages(self, user_id: int, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves raw messages from the chat history."""
        pass

    @abstractmethod
    def get_summary(self, user_id: int, session_id: str) -> str:
        """Retrieves the current conversation summary."""
        pass

    @abstractmethod
    def update_summary(self, user_id: int, session_id: str, new_summary: str, summarized_message_ids: List[str]) -> None:
        """Updates the conversation summary and marks the specified messages as summarized."""
        pass
