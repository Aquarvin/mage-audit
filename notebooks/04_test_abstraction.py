"""Day 4: Test the LLM provider abstraction layer."""

import asyncio
from pathlib import Path

from src.core.config import settings
from src.core.llm import LLMMessage, Role, get_llm_provider

SAMPLE_FILE = Path("notebooks/samples/bad_module.php")


async def main():
    # Create provider via factory — one line, configured by .env
    llm = get_llm_provider(settings.llm_provider)
    print(f"Using provider: {settings.llm_provider}, model: {llm.model}")

    # Load PHP code
    code = SAMPLE_FILE.read_text(encoding="utf-8")

    # Build messages in our universal format
    messages = [
        LLMMessage(
            role=Role.SYSTEM,
            content=(
                "You are a senior Magento 2 developer performing code review. "
                "Return findings as a JSON array. Each finding: "
                '{"severity": "critical|error|warning|info", '
                '"line": <number>, '
                '"category": "security|bug|architecture|performance|style", '
                '"issue": "<description>", '
                '"suggestion": "<how to fix>"}. '
                "Return ONLY valid JSON, no markdown."
            ),
        ),
        LLMMessage(
            role=Role.USER,
            content=f"Review this code:\n\n```php\n{code}\n```",
        ),
    ]

    # Call through abstraction — this code works with ANY provider
    print("\n--- Calling LLM ---\n")
    response = await llm.complete(messages, temperature=0.3)

    print(f"Content:\n{response.content}\n")
    print(f"Model: {response.model}")
    print(
        f"Tokens: {response.usage.input_tokens} in, "
        f"{response.usage.output_tokens} out, "
        f"{response.usage.thinking_tokens} thinking"
    )
    print(f"Total: {response.usage.total_tokens}")
    print(f"Finish: {response.finish_reason}")

    # Test streaming
    print("\n--- Streaming test ---\n")
    stream_messages = [
        LLMMessage(role=Role.USER, content="Name 3 PHP frameworks in one line."),
    ]

    async for chunk in llm.stream(stream_messages, temperature=0.3):
        print(chunk, end="", flush=True)
    print("\n\n--- Done ---")


asyncio.run(main())
