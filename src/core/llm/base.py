"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from pydantic import BaseModel

from src.core.llm.types import LLMMessage, LLMResponse


class LLMProvider(ABC):
    """Abstract interface that all LLM providers must implement.

    This is the contract. Code that uses LLMs depends only on this
    interface, never on concrete providers (Gemini, Claude, etc.).
    """

    def __init__(self, model: str) -> None:
        self.model = model

    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        response_schema: type[BaseModel] | None = None,
    ) -> LLMResponse:
        """Generate a completion for the given messages.

        Args:
            messages: Conversation history.
            temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative).
            response_schema: Optional Pydantic model to enforce structured JSON output.

        Returns:
            A provider-agnostic LLMResponse.
        """
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream a completion token by token.

        Yields:
            Chunks of generated text as they arrive.
        """
        ...
