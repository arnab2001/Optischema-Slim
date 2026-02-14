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

    @property
    def name(self) -> str:
        return "deepseek"

    @property
    def model_name(self) -> str:
        return self.model

    async def generate(self, prompt: str, max_tokens: int = 512) -> str:
        """
        Generate raw text response from DeepSeek.
        """
        if not self.client:
            return "Error: DeepSeek client not initialized. Check API key."
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens
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

            # Capture token usage
            token_usage = None
            if hasattr(response, 'usage') and response.usage:
                u = response.usage
                logger.info(
                    f"[DeepSeek] Token usage: prompt={u.prompt_tokens}, "
                    f"completion={u.completion_tokens}, total={u.total_tokens}, "
                    f"model={self.model}"
                )
                token_usage = {
                    "prompt_tokens": u.prompt_tokens,
                    "completion_tokens": u.completion_tokens,
                    "total_tokens": u.total_tokens,
                    "model": self.model,
                    "provider": "deepseek"
                }

            try:
                result = json.loads(content)
                parsed = {
                    "category": result.get("category", "ADVISORY"),
                    "reasoning": result.get("reasoning", ""),
                    "sql": result.get("sql"),
                    "confidence": result.get("confidence", 0.7)
                }
                if token_usage:
                    parsed["_token_usage"] = token_usage
                return parsed
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

    async def complete(self, prompt: str) -> Dict[str, Any]:
        """Raw JSON completion — returns LLM response without reshaping into category/reasoning/sql."""
        if not self.client:
            return {"error": "DeepSeek client not initialized."}

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            result = json.loads(content)

            if hasattr(response, 'usage') and response.usage:
                u = response.usage
                logger.info(
                    f"[DeepSeek] Token usage: prompt={u.prompt_tokens}, "
                    f"completion={u.completion_tokens}, total={u.total_tokens}, "
                    f"model={self.model}"
                )
                result["_token_usage"] = {
                    "prompt_tokens": u.prompt_tokens,
                    "completion_tokens": u.completion_tokens,
                    "total_tokens": u.total_tokens,
                    "model": self.model,
                    "provider": "deepseek"
                }

            return result
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse DeepSeek response as JSON")
            return {"error": "Failed to parse response as JSON"}
        except Exception as e:
            logger.error(f"DeepSeek completion failed: {e}")
            return {"error": str(e)}
