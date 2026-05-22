"""Domain types for LLM interactions, provider-agnostic."""

from enum import StrEnum

from pydantic import BaseModel


class Role(StrEnum):
    """Message role in a conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class LLMMessage(BaseModel):
    """A single message in a conversation."""

    role: Role
    content: str


class TokenUsage(BaseModel):
    """Token usage statistics for a single LLM call."""

    input_tokens: int = 0
    output_tokens: int = 0
    # Some models (Gemini 2.5, o1) have hidden "thinking" tokens
    thinking_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens + self.thinking_tokens


class LLMResponse(BaseModel):
    """Provider-agnostic response from an LLM."""

    content: str
    model: str
    usage: TokenUsage
    # Raw provider response for debugging, not always populated
    finish_reason: str | None = None
