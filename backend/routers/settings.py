"""
Settings Router for OptiSchema Slim.
Handles API endpoints for user settings.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any

from storage import get_all_settings, set_all_settings, get_saved_optimizations, delete_saved_optimization

router = APIRouter(
    prefix="/api",
    tags=["settings"]
)

class SettingsModel(BaseModel):
    llm_provider: Optional[str] = "ollama"
    ollama_base_url: Optional[str] = "http://localhost:11434"
    ollama_model: Optional[str] = "sqlcoder"
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = "gpt-4o-mini"
    gemini_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    privacy_mode: Optional[bool] = False

@router.get("/settings")
async def get_settings():
    """Get all user settings."""
    settings = await get_all_settings()
    return settings

@router.post("/settings")
async def save_settings(data: SettingsModel):
    """Save user settings."""
    settings_dict = data.model_dump(exclude_none=True)
    await set_all_settings(settings_dict)
    return {"success": True}

from llm.factory import LLMFactory

@router.post("/settings/llm/test")
async def test_llm_connection(data: SettingsModel):
    """
    Test connection to an LLM provider with the provided settings.
    Does NOT save the settings.
    """
    try:
        provider_name = data.llm_provider.lower()
        provider = None
        
        if provider_name == "ollama":
            from llm.ollama_provider import OllamaProvider
            provider = OllamaProvider(base_url=data.ollama_base_url, model=data.ollama_model)
        elif provider_name == "openai":
            from llm.openai_provider import OpenAIProvider
            provider = OpenAIProvider(api_key=data.openai_api_key, model=data.openai_model)
        elif provider_name == "gemini":
            from llm.gemini_provider import GeminiProvider
            provider = GeminiProvider(api_key=data.gemini_api_key)
        elif provider_name == "deepseek":
            from llm.deepseek_provider import DeepSeekProvider
            provider = DeepSeekProvider(api_key=data.deepseek_api_key)
            
        if not provider:
            return {"success": False, "message": f"Unknown provider: {provider_name}"}
            
        # Test with a simple prompt
        test_prompt = "Say 'OK' if you can read this."
        response = await provider.generate(test_prompt, max_tokens=10)
        
        if "Error" in response:
            return {"success": False, "message": response}
            
        return {"success": True, "message": f"Successfully connected to {provider_name}!", "response": response}
        
    except Exception as e:
        return {"success": False, "message": f"Connection test failed: {str(e)}"}

@router.get("/optimizations/saved")
async def get_saved():
    """Get all saved optimizations."""
    optimizations = await get_saved_optimizations()
    return optimizations

@router.delete("/optimizations/saved/{opt_id}")
async def delete_saved(opt_id: str):
    """Delete a saved optimization."""
    await delete_saved_optimization(opt_id)
    return {"success": True}
