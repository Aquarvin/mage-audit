"""Unit tests for LLM abstraction layer — no API calls needed."""

from src.core.llm import LLMMessage, LLMResponse, Role, TokenUsage


def test_llm_message_creation():
    """LLMMessage should be created with role and content."""
    msg = LLMMessage(role=Role.SYSTEM, content="You are a helpful assistant.")
    assert msg.role == Role.SYSTEM
    assert msg.content == "You are a helpful assistant."


def test_llm_message_user():
    """User messages should work."""
    msg = LLMMessage(role=Role.USER, content="Review my code.")
    assert msg.role == Role.USER


def test_token_usage_total():
    """Total tokens should sum input + output + thinking."""
    usage = TokenUsage(input_tokens=100, output_tokens=50, thinking_tokens=200)
    assert usage.total_tokens == 350


def test_token_usage_defaults():
    """Token usage should default to zero."""
    usage = TokenUsage()
    assert usage.input_tokens == 0
    assert usage.output_tokens == 0
    assert usage.thinking_tokens == 0
    assert usage.total_tokens == 0


def test_llm_response_structure():
    """LLMResponse should hold content, model, and usage."""
    response = LLMResponse(
        content="LGTM",
        model="gemini-2.5-flash",
        usage=TokenUsage(input_tokens=10, output_tokens=5),
    )
    assert response.content == "LGTM"
    assert response.model == "gemini-2.5-flash"
    assert response.usage.total_tokens == 15
    assert response.finish_reason is None


def test_factory_unknown_provider():
    """Factory should raise ValueError for unknown providers."""
    import pytest

    from src.core.llm import get_llm_provider

    with pytest.raises(ValueError, match="Unknown LLM provider"):
        get_llm_provider("nonexistent")


def test_factory_unimplemented_provider():
    """Factory should raise NotImplementedError for planned providers."""
    import pytest

    from src.core.llm import get_llm_provider

    with pytest.raises(NotImplementedError):
        get_llm_provider("anthropic")

    with pytest.raises(NotImplementedError):
        get_llm_provider("openai")

    with pytest.raises(NotImplementedError):
        get_llm_provider("ollama")
