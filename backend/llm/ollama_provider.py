"""
Ollama Provider implementation.
Handles communication with local Ollama instance.
"""

import logging
import json
import aiohttp
from typing import Dict, Any
from .base import LLMProvider
from config import settings

logger = logging.getLogger(__name__)

class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_model

    async def generate(self, prompt: str) -> str:
        """
        Generate raw text response.
        """
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
                async with session.post(f"{self.base_url}/api/generate", json=payload) as response:
                    if response.status != 200:
                        logger.error(f"Ollama API error: {response.status}")
                        return f"Error: {response.status}"
                    
                    data = await response.json()
                    return data.get("response", "")
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return f"Error: {str(e)}"

    async def analyze(self, prompt: str) -> Dict[str, Any]:
        """
        Analyze query and return JSON.
        """
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                }
                async with session.post(f"{self.base_url}/api/generate", json=payload) as response:
                    if response.status != 200:
                        return {"error": f"Ollama API error: {response.status}"}
                    
                    data = await response.json()
                    response_text = data.get("response", "{}")
                    
                    try:
                        return json.loads(response_text)
                    except json.JSONDecodeError:
                        return {"error": "Failed to parse LLM response as JSON", "raw_response": response_text}
                        
        except Exception as e:
            logger.error(f"Ollama analysis failed: {e}")
            return {"error": str(e)}
