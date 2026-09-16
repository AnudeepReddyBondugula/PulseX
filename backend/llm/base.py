"""Abstract interface every LLM provider must implement.

Calling code depends only on this interface, never on a vendor SDK, so
adding or swapping a provider means writing a new file in providers/
rather than touching callers.
"""

from abc import ABC, abstractmethod


class LLMProviderError(Exception):
    """Raised when a provider fails to generate a response."""


class LLMProvider(ABC):
    """A text-generation backend."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Return the model's text response to a prompt."""
        raise NotImplementedError
