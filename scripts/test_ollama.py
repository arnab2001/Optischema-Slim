"""
Test script for Ollama integration.
Verifies that the backend can connect to a local Ollama instance.
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from analysis.providers import OllamaProvider
from config import settings

async def test_ollama():
    print(f"Testing Ollama connection...")
    print(f"URL: {settings.ollama_base_url}")
    print(f"Model: {settings.ollama_model}")
    
    provider = OllamaProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model
    )
    
    try:
        print("\nSending test prompt: 'Hello, are you working?'")
        response = await provider.generate("Hello, are you working?", max_tokens=50)
        print(f"\nSuccess! Response:\n{response}")
        return True
    except Exception as e:
        print(f"\nFailed: {e}")
        print("\nTroubleshooting:")
        print("1. Is Ollama running? (Run 'ollama serve')")
        print(f"2. Is the model '{settings.ollama_model}' pulled? (Run 'ollama pull {settings.ollama_model}')")
        print(f"3. Is the URL correct? ({settings.ollama_base_url})")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_ollama())
    sys.exit(0 if success else 1)
