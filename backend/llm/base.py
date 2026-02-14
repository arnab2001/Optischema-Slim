"""
Abstract Base Class for LLM Providers.
Defines the interface for generating text and analyzing queries.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class LLMProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the internal provider name (e.g. 'ollama', 'openai')."""
        pass

    @property
    def model_name(self) -> str:
        """Return the specific model name being used (e.g. 'sqlcoder:7b', 'deepseek-r1')."""
        return "unknown"

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """
        Generate a raw text response from the LLM.
        """
        pass

    @abstractmethod
    async def analyze(self, prompt: str) -> Dict[str, Any]:
        """
        Analyze a query and return a structured JSON response.
        """
        pass

    async def complete(self, prompt: str) -> Dict[str, Any]:
        """
        Generic JSON completion — returns LLM response as-is without reshaping.
        Default falls back to analyze(). Providers that reshape in analyze()
        should override this.
        """
        return await self.analyze(prompt)
