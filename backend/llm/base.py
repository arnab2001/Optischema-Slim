"""
Abstract Base Class for LLM Providers.
Defines the interface for generating text and analyzing queries.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class LLMProvider(ABC):
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
