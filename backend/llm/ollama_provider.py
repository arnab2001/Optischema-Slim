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
        self.base_url = (base_url or settings.ollama_base_url).rstrip('/')
        self.model = model or settings.ollama_model

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self.model

    async def generate(self, prompt: str, max_tokens: int = 512) -> str:
        """
        Generate raw text response.
        """
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": 0.2
                    }
                }
                async with session.post(f"{self.base_url}/api/generate", json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Ollama API error: {response.status} - {error_text}")
                        return f"Error: {response.status}"
                    
                    data = await response.json()
                    return data.get("response", "").strip()
        except aiohttp.ClientConnectorError:
            error_msg = f"Could not connect to Ollama at {self.base_url}. Is it running?"
            logger.error(error_msg)
            return f"Error: {error_msg}"
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return f"Error: {str(e)}"

    async def analyze(self, prompt: str, max_tokens: int = 1024) -> Dict[str, Any]:
        """
        Analyze query and return JSON.
        """
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": 0.1
                    }
                }
                async with session.post(f"{self.base_url}/api/generate", json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return {"error": f"Ollama API error: {response.status}", "details": error_text}
                    
                    data = await response.json()
                    response_text = data.get("response", "{}").strip()

                    # Log token usage
                    prompt_tokens = data.get("prompt_eval_count", 0)
                    completion_tokens = data.get("eval_count", 0)
                    if prompt_tokens or completion_tokens:
                        logger.info(
                            f"[Ollama] Token usage: prompt={prompt_tokens}, "
                            f"completion={completion_tokens}, "
                            f"total={prompt_tokens + completion_tokens}, "
                            f"model={self.model}"
                        )

                    try:
                        return json.loads(response_text)
                    except json.JSONDecodeError:
                        # Fallback: try to find the JSON block if it's wrapped in text
                        import re
                        json_match = re.search(r'(\{.*\})', response_text, re.DOTALL)
                        if json_match:
                            try:
                                return json.loads(json_match.group(1))
                            except:
                                pass
                        return {"error": "Failed to parse LLM response as JSON", "raw_response": response_text}
                        
        except aiohttp.ClientConnectorError:
            return {"error": f"Could not connect to Ollama at {self.base_url}. Is it running?"}
        except Exception as e:
            logger.error(f"Ollama analysis failed: {e}")
            return {"error": str(e)}
