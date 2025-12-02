"""
LLM Provider abstractions and implementations.
Supports Gemini, DeepSeek, and Ollama (Local).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import aiohttp
import logging
import json
from config import settings

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate(self, prompt: str, max_tokens: int = 512) -> str:
        """Generate text from prompt."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

class GeminiProvider(LLMProvider):
    """Google Gemini provider."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    
    @property
    def name(self) -> str:
        return "gemini"
        
    async def generate(self, prompt: str, max_tokens: int = 512) -> str:
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": self.api_key
        }
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": 0.2
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["candidates"][0]["content"]["parts"][0]["text"].strip()
                else:
                    error_text = await response.text()
                    raise Exception(f"Gemini API error: {response.status} - {error_text}")

class DeepSeekProvider(LLMProvider):
    """DeepSeek provider."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://api.deepseek.com/v1/chat/completions"
        
    @property
    def name(self) -> str:
        return "deepseek"
    
    async def generate(self, prompt: str, max_tokens: int = 512) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.2
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, headers=headers, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"].strip()
                else:
                    error_text = await response.text()
                    raise Exception(f"DeepSeek API error: {response.status} - {error_text}")

class OllamaProvider(LLMProvider):
    """Local Ollama provider."""
    
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.url = f"{self.base_url}/api/generate"
        
    @property
    def name(self) -> str:
        return "ollama"
    
    async def generate(self, prompt: str, max_tokens: int = 512) -> str:
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.2
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["response"].strip()
                    else:
                        error_text = await response.text()
                        raise Exception(f"Ollama API error: {response.status} - {error_text}")
        except aiohttp.ClientConnectorError:
            raise Exception(f"Could not connect to Ollama at {self.base_url}. Is it running?")

class LLMFactory:
    """Factory to get the active LLM provider."""
    
    @staticmethod
    def get_provider() -> LLMProvider:
        provider_name = settings.llm_provider.lower()
        
        if provider_name == "gemini":
            if not settings.gemini_api_key:
                logger.warning("Gemini API key not found")
            return GeminiProvider(settings.gemini_api_key)
            
        elif provider_name == "deepseek":
            if not settings.deepseek_api_key:
                logger.warning("DeepSeek API key not found")
            return DeepSeekProvider(settings.deepseek_api_key)
            
        elif provider_name == "ollama":
            return OllamaProvider(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model
            )
            
        else:
            raise ValueError(f"Unknown LLM provider: {provider_name}")
