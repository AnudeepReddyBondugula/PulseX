from llm.base import LLMProvider
from pipeline.config import get_logger
from openrouter import OpenRouter, RateLimitError

logger = get_logger(__name__)

class OpenRouterProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "openrouter/free"):
        self._model = "nvidia/nemotron-3.5-lightning:free"
        self._client = OpenRouter(api_key=api_key)

    def generate(self, prompt: str) -> str:
        # Implement the logic to call the OpenRouter API with the provided prompt
        # and return the generated text response.
        
        try:
            response = self._client.chat.send(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                    stream=False
                )
                    
            return response.choices[0].message.content
        except Exception as e:
            logger.error("Error generating text with OpenRouter: %s", e)
            raise
