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
