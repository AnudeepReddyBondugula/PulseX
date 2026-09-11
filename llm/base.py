"""
base.py — Abstract interface every LLM provider must implement.

Calling code (summarizer.py, and later the explain/chat endpoints) depends
only on this interface — never on a vendor SDK directly. Swapping or adding
a provider means writing a new file in this folder, not touching callers.
"""

from abc import ABC, abstractmethod


class LLMProviderError(Exception):
    """Raised when a provider fails to generate a response after all retries."""


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Return the model's text response to `prompt`."""
        raise NotImplementedError