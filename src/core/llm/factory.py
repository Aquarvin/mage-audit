"""Factory for creating LLM providers based on configuration."""

from src.core.llm.base import LLMProvider


def get_llm_provider(provider_name: str, model: str = "") -> LLMProvider:
    """Create an LLM provider instance by name.

    Args:
        provider_name: One of 'gemini', 'anthropic', 'openai', 'ollama'.
        model: Optional model override. If empty, uses default from settings.

    Returns:
        An LLMProvider instance.

    Raises:
        ValueError: If provider_name is not supported.
    """
    match provider_name:
        case "gemini":
            from src.core.llm.gemini import GeminiProvider

            return GeminiProvider(model=model)

        case "anthropic":
            raise NotImplementedError(
                "Anthropic provider coming in Phase 3. Set LLM_PROVIDER=gemini in .env"
            )

        case "openai":
            raise NotImplementedError(
                "OpenAI provider coming in Phase 3. Set LLM_PROVIDER=gemini in .env"
            )

        case "ollama":
            raise NotImplementedError(
                "Ollama provider coming in Phase 5. Set LLM_PROVIDER=gemini in .env"
            )

        case _:
            raise ValueError(
                f"Unknown LLM provider: {provider_name}. "
                f"Supported: gemini, anthropic, openai, ollama"
            )
