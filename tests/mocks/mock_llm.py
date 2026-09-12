from typing import Any, Type

from core.interfaces.llm_provider import LLMProviderInterface


class MockLLMResponse:
    def __init__(self, content):
        self.content = content


class MockLLMProvider(LLMProviderInterface):
    def __init__(self, default_response: str = "Mocked response"):
        self.default_response = default_response
        self.calls = []

    def invoke(self, prompt: str | list) -> Any:
        self.calls.append(prompt)
        return MockLLMResponse(self.default_response)

    def with_structured_output(self, schema: Type) -> "LLMProviderInterface":
        return self
