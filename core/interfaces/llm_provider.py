from abc import ABC, abstractmethod
from typing import Any, Type


class LLMProviderInterface(ABC):
    @abstractmethod
    def invoke(self, prompt: str | list) -> Any:
        """Return something with a `.content` attribute."""
        pass

    @abstractmethod
    def with_structured_output(self, schema: Type) -> "LLMProviderInterface":
        pass
