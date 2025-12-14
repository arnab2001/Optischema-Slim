"""
LLM Factory.
Instantiates the correct LLM provider based on configuration.
Now reads from SQLite settings dynamically.
"""

import logging
from typing import Optional
from config import settings
from storage import get_setting
from .base import LLMProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider
from .deepseek_provider import DeepSeekProvider

logger = logging.getLogger(__name__)


class LLMFactory:
    @staticmethod
    async def get_provider_async() -> LLMProvider:
        """
        Get the configured LLM provider from database settings.
        Falls back to environment variables if not set in database.
        """
        # Try to read from SQLite settings first (UI overrides .env)
        db_provider = await get_setting("llm_provider")
        env_provider = settings.llm_provider
        provider_name = (db_provider or env_provider).lower()
        
        logger.info(f"[LLMFactory] DB provider: '{db_provider}', ENV provider: '{env_provider}' → Using: '{provider_name}'")
        
        if provider_name == "ollama":
            base_url = await get_setting("ollama_base_url") or settings.ollama_base_url
            model = await get_setting("ollama_model") or settings.ollama_model
            return OllamaProvider(base_url=base_url, model=model)
        
        elif provider_name == "openai":
            api_key = await get_setting("openai_api_key") or settings.openai_api_key
            model = await get_setting("openai_model") or settings.openai_model
            return OpenAIProvider(api_key=api_key, model=model)
        
        elif provider_name == "gemini":
            db_api_key = await get_setting("gemini_api_key")
            env_api_key = settings.gemini_api_key
            api_key = db_api_key or env_api_key
            logger.info(f"[Gemini] DB key: {'set' if db_api_key else 'empty'}, ENV key: {'set' if env_api_key else 'empty'}")
            if not api_key:
                logger.warning("[Gemini] No API key found in database or environment!")
            return GeminiProvider(api_key=api_key)
        
        elif provider_name == "deepseek":
            db_api_key = await get_setting("deepseek_api_key")
            env_api_key = settings.deepseek_api_key
            api_key = db_api_key or env_api_key
            logger.info(f"[DeepSeek] DB key: {'set' if db_api_key else 'empty'}, ENV key: {'set' if env_api_key else 'empty'}")
            if not api_key:
                logger.warning("[DeepSeek] No API key found in database or environment!")
            return DeepSeekProvider(api_key=api_key)
        
        else:
            # Default to Ollama if unknown
            logger.warning(f"Unknown LLM provider '{provider_name}', defaulting to Ollama")
            return OllamaProvider()

    @staticmethod
    def get_provider() -> LLMProvider:
        """
        Synchronous version that reads from environment variables only.
        Use get_provider_async for database settings.
        """
        provider_name = settings.llm_provider.lower()
        
        if provider_name == "ollama":
            return OllamaProvider()
        elif provider_name == "openai":
            return OpenAIProvider()
        elif provider_name == "gemini":
            return GeminiProvider(api_key=settings.gemini_api_key)
        elif provider_name == "deepseek":
            return DeepSeekProvider(api_key=settings.deepseek_api_key)
        else:
            return OllamaProvider()
