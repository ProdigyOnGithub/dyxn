import requests
import json
from typing import Any, Type
from core.interfaces.llm_provider import LLMProviderInterface

class GeminiResponse:
    def __init__(self, content: str):
        self.content = content

class GeminiProvider(LLMProviderInterface):
    def __init__(self, api_key: str, model: str = "gemini-3.1-flash-lite", force_json: bool = False):
        if not api_key:
            raise ValueError("Gemini API Key is missing. Please add it to your .env file.")
        
        self.api_key = api_key
        self.model = model
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        self.force_json = force_json

    def invoke(self, prompt: str | list) -> Any:
        # Robustly handle both string prompts and chat history arrays by collapsing them
        if isinstance(prompt, list):
            text_prompt = "\n\n".join([f"{msg.get('role', 'user').upper()}:\n{msg.get('content', '')}" for msg in prompt])
        else:
            text_prompt = prompt
            
        data = {
            "contents": [{"parts": [{"text": text_prompt}]}]
        }
        
        if self.force_json:
            data["generationConfig"] = {"responseMimeType": "application/json"}
            
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(self.url, headers=headers, json=data)
        
        if response.status_code != 200:
            raise Exception(f"Gemini API Error: {response.text}")
            
        try:
            content = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            content = ""
            
        if self.force_json:
            class Struct:
                def __init__(self, **entries):
                    self.__dict__.update(entries)
            try:
                return Struct(**json.loads(content))
            except json.JSONDecodeError:
                return GeminiResponse(content)
                
        return GeminiResponse(content)

    def with_structured_output(self, schema: Type) -> "LLMProviderInterface":
        return GeminiProvider(api_key=self.api_key, model=self.model, force_json=True)
