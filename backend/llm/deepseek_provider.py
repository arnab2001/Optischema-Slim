"""
DeepSeek LLM Provider for OptiSchema Slim.
Uses OpenAI-compatible API.
"""

import logging
import json
from typing import Dict, Any
from .base import LLMProvider

logger = logging.getLogger(__name__)


class DeepSeekProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        self.api_key = api_key
        self.model = model or "deepseek-chat"
        self.base_url = "https://api.deepseek.com/v1"  # Note: /v1 required for OpenAI compatibility
        self.client = None
        
        if self.api_key:
            try:
                import openai
                self.client = openai.AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
                logger.info(f"[DeepSeek] Initialized with model: {self.model}")
            except ImportError:
                logger.warning("openai package not installed. Install with: pip install openai")
            except Exception as e:
                logger.error(f"Failed to initialize DeepSeek client: {e}")

    async def generate(self, prompt: str) -> str:
        """
        Generate raw text response from DeepSeek.
        """
        if not self.client:
            return "Error: DeepSeek client not initialized. Check API key."
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"DeepSeek generate failed: {e}")
            return f"Error: {str(e)}"

    async def analyze(self, prompt: str) -> Dict[str, Any]:
        """
        Analyze query using DeepSeek with JSON output.
        """
        if not self.client:
            return {
                "category": "ADVISORY",
                "reasoning": "DeepSeek client not initialized. Please check your API key in Settings.",
                "sql": None,
                "confidence": 0.0
            }

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            
            try:
                result = json.loads(content)
                return {
                    "category": result.get("category", "ADVISORY"),
                    "reasoning": result.get("reasoning", ""),
                    "sql": result.get("sql"),
                    "confidence": result.get("confidence", 0.7)
                }
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse DeepSeek response as JSON: {content[:200]}")
                return {
                    "category": "ADVISORY",
                    "reasoning": content,
                    "sql": None,
                    "confidence": 0.5
                }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"DeepSeek analysis failed: {error_msg}")
            return {
                "category": "ADVISORY",
                "reasoning": f"Error communicating with DeepSeek: {error_msg}",
                "sql": None,
                "confidence": 0.0
            }
