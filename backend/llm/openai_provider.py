"""
OpenAI Provider implementation.
Handles communication with OpenAI API.
"""

import logging
import json
from typing import Dict, Any
from .base import LLMProvider
from config import settings

logger = logging.getLogger(__name__)

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        # We import openai here to avoid hard dependency if not used
        try:
            import openai
            self.client = openai.AsyncOpenAI(api_key=self.api_key)
        except ImportError:
            self.client = None
            logger.warning("OpenAI library not installed. Please install 'openai' package.")

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self.model

    async def generate(self, prompt: str, max_tokens: int = 512) -> str:
        """
        Generate raw text response.
        """
        if not self.client:
            return "Error: OpenAI library not installed."
        if not self.api_key:
            return "Error: OpenAI API key not configured."

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return f"Error: {str(e)}"

    async def analyze(self, prompt: str) -> Dict[str, Any]:
        """
        Analyze query and return JSON.
        """
        if not self.client:
            return {"error": "OpenAI library not installed."}
        if not self.api_key:
            return {"error": "OpenAI API key not configured."}

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content

            # Log token usage
            if hasattr(response, 'usage') and response.usage:
                u = response.usage
                logger.info(
                    f"[OpenAI] Token usage: prompt={u.prompt_tokens}, "
                    f"completion={u.completion_tokens}, total={u.total_tokens}, "
                    f"model={self.model}"
                )

            return json.loads(content)
        except Exception as e:
            logger.error(f"OpenAI analysis failed: {e}")
            return {"error": str(e)}
