"""
gemini_provider.py — Concrete LLMProvider backed by the Gemini API.

This is the ONLY file in the codebase that imports the `google-generativeai` package.
"""

import time
from typing import Optional

from google import genai
from google.genai import errors

from pipeline.config import get_logger
from pipeline.llm.base import LLMProvider, LLMProviderError

logger = get_logger(__name__)

MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 2


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def generate(self, prompt: str, max_tokens: int = 200) -> str:
        last_exc: Optional[Exception] = None

        for _ in range(1, MAX_RETRIES + 1):
            try:
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=[{"role": "user", "content": prompt}],
                )
                return response.text

            except errors.APIError as e:
                last_exc = e
                # 1. Handling "RateLimitError" (HTTP 429)
                if e.code == 429:
                    print(f"Rate Limit Exceeded: {e.message}")
                    # Implement exponential backoff here
                    
                # 2. Handling "APIStatusError" (Other HTTP Status Errors like 400, 404, 500)
                elif e.code == 404:
                    print(f"Model not found or invalid endpoint: {e.message}")
                elif e.code == 400:
                    print(f"Invalid request / Bad Syntax: {e.message}")
                elif e.code and e.code >= 500:
                    print(f"Google Server Error ({e.code}): {e.message}")
                else:
                    print(f"General API Error ({e.code}): {e.message}")

            # 3. Handling "APIConnectionError" (Network/Timeout failures before hitting the API)
            except Exception as e:
                last_exc = e
                # Standard Python network exceptions (like requests.exceptions.ConnectionError 
                # or urllib3 errors) are caught here if the SDK cannot reach Google servers.
                print(f"Network connection failed: {e}")
                logger.error("genai API call failed after %d attempts", MAX_RETRIES)
        raise LLMProviderError(
            f"Gemini API call failed after {MAX_RETRIES} attempts"
        ) from last_exc