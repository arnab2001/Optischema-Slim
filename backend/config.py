"""
Configuration module for OptiSchema backend.
Handles environment variables and application settings.
"""

import os
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", env="OPENAI_MODEL")
    
    # Backend Configuration
    backend_host: str = Field(default="0.0.0.0", env="BACKEND_HOST")
    backend_port: int = Field(default=8080, env="BACKEND_PORT")
    backend_reload: bool = Field(default=True, env="BACKEND_RELOAD")
    
    # Environment Configuration
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Cache Configuration
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")  # 1 hour
    cache_size: int = Field(default=1000, env="CACHE_SIZE")
    
    # Analysis Configuration
    polling_interval: int = Field(default=30, env="POLLING_INTERVAL")  # seconds
    top_queries_limit: int = Field(default=10, env="TOP_QUERIES_LIMIT")
    analysis_interval: int = Field(default=60, env="ANALYSIS_INTERVAL")  # seconds
    
    # LLM Configuration
    gemini_api_key: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    deepseek_api_key: Optional[str] = Field(default=None, env="DEEPSEEK_API_KEY")
    llm_provider: str = Field(default="gemini", env="LLM_PROVIDER")
    
    # Ollama Configuration (Local LLM)
    ollama_base_url: str = Field(default="http://host.docker.internal:11434", env="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3", env="OLLAMA_MODEL")

    class Config:
        # Look for .env in current dir (backend/) OR parent dir (root)
        env_file = [".env", "../.env"]
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings
