from abc import ABC, abstractmethod
from typing import Any, Dict

from core.config import Config
from core.interfaces.llm_provider import LLMProviderInterface
from core.logging import get_logger


class BaseAgent(ABC):
    def __init__(self, llm: LLMProviderInterface, config: Config):
        self.llm = llm
        self.config = config
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph node. Mutate/return state."""
        pass
