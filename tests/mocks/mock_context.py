from typing import Any, Dict

from core.interfaces.context_provider import ContextProviderInterface


class MockContextProvider(ContextProviderInterface):
    def __init__(self):
        self.messages = []
        self.summary = ""

    def save_message(self, user_id: int, session_id: str, role: str, message: str) -> None:
        self.messages.append({"role": role, "content": message})

    def get_context(self, user_id: int, session_id: str, window_size: int = 5) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "recent_messages": self.messages[-window_size:] if self.messages else [],
        }

    def summarize(self, user_id: int, session_id: str, window_size: int = 5) -> None:
        if len(self.messages) > window_size:
            self.summary = "Mock summary of older messages."
