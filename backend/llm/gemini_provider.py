"""
Gemini LLM Provider for OptiSchema Slim.
Uses the official google-genai SDK.
"""

import logging
import json
from typing import Dict, Any
import asyncio

from .base import LLMProvider

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model = model or "gemini-2.0-flash"
        self.client = None
        
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                logger.info(f"[Gemini] Initialized with model: {self.model}")
            except ImportError:
                logger.warning("google-genai package not installed. Install with: pip install google-genai")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")

    async def generate(self, prompt: str) -> str:
        """
        Generate raw text response from Gemini.
        """
        if not self.client:
            return "Error: Gemini client not initialized. Check API key and install google-genai package."

        try:
            # Run in thread pool since the SDK is synchronous
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=self.model,
                    contents=prompt
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini generate failed: {e}")
            return f"Error: {str(e)}"

    async def analyze(self, prompt: str) -> Dict[str, Any]:
        """
        Analyze query using Gemini with JSON output.
        """
        if not self.client:
            return {
                "category": "ADVISORY",
                "reasoning": "Gemini client not initialized. Please check your API key in Settings and ensure google-genai is installed.",
                "sql": None,
                "confidence": 0.0
            }

        try:
            # Run in thread pool since the SDK is synchronous
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "temperature": 0.1
                    }
                )
            )
            
            text = response.text
            
            # Parse JSON response
            try:
                # Clean up markdown code blocks if present
                if text.startswith("```"):
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                text = text.strip()
                
                result = json.loads(text)
                return {
                    "category": result.get("category", "ADVISORY"),
                    "reasoning": result.get("reasoning", ""),
                    "sql": result.get("sql"),
                    "confidence": result.get("confidence", 0.7)
                }
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse Gemini response as JSON: {text[:200]}")
                return {
                    "category": "ADVISORY",
                    "reasoning": text,
                    "sql": None,
                    "confidence": 0.5
                }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Gemini analysis failed: {error_msg}")
            
            # Handle rate limiting gracefully
            if "429" in error_msg or "quota" in error_msg.lower():
                return {
                    "category": "ADVISORY",
                    "reasoning": "Rate limited by Gemini API. Please wait a moment and try again, or upgrade your API quota.",
                    "sql": None,
                    "confidence": 0.0
                }
            
            return {
                "category": "ADVISORY",
                "reasoning": f"Error communicating with Gemini: {error_msg}",
                "sql": None,
                "confidence": 0.0
            }
