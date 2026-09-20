import requests
from typing import Any, Type
from core.interfaces.llm_provider import LLMProviderInterface

class GroqResponse:
    def __init__(self, content: str):
        self.content = content

class GroqProvider(LLMProviderInterface):
    def __init__(self, api_key: str, model: str = "openai/gpt-oss-20b", force_json: bool = False):
        if not api_key:
            raise ValueError("Groq API Key is missing. Please add it to your .env file.")
        
        self.api_key = api_key
        self.model = model
        self.url = "https://api.groq.com/openai/v1/chat/completions"
        self.force_json = force_json

    def invoke(self, prompt: str | list) -> Any:
        messages = prompt if isinstance(prompt, list) else [{"role": "user", "content": prompt}]
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": messages
        }
        
        if self.force_json:
            data["response_format"] = {"type": "json_object"}
            
        response = requests.post(self.url, headers=headers, json=data)
        
        # If there's an API error, raise an exception so the user knows
        if response.status_code != 200:
            raise Exception(f"Groq API Error: {response.text}")
            
        content = response.json()["choices"][0]["message"]["content"]
        
        if self.force_json:
            import json
            class Struct:
                def __init__(self, **entries):
                    self.__dict__.update(entries)
            try:
                return Struct(**json.loads(content))
            except json.JSONDecodeError:
                # fallback if it's not valid json
                return GroqResponse(content)
                
        return GroqResponse(content)

    def with_structured_output(self, schema: Type) -> "LLMProviderInterface":
        return GroqProvider(api_key=self.api_key, model=self.model, force_json=True)
