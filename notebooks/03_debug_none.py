"""Debug: why experiment 2 returned None."""

import asyncio
from pathlib import Path
from google import genai
from src.core.config import settings

SAMPLE_FILE = Path("notebooks/samples/bad_module.php")


async def main():
    client = genai.Client(api_key=settings.google_api_key)
    code = SAMPLE_FILE.read_text(encoding="utf-8")

    response = await client.aio.models.generate_content(
        model=settings.llm_model,
        contents=(
            "You are a senior Magento 2 / Adobe Commerce developer "
            "with 10+ years of experience. You specialize in code review "
            "and finding bugs, security issues, and architecture problems.\n\n"
            "Review this code. Be specific — mention line numbers, "
            "explain why each issue matters, and suggest a fix.\n\n"
            f"```php\n{code}\n```"
        ),
    )

    print(f"response.text: {response.text}")
    print(f"candidates count: {len(response.candidates)}")

    for i, candidate in enumerate(response.candidates):
        print(f"\n--- Candidate {i} ---")
        print(f"finish_reason: {candidate.finish_reason}")
        print(f"parts count: {len(candidate.content.parts) if candidate.content else 0}")
        if candidate.content:
            for j, part in enumerate(candidate.content.parts):
                print(f"  part {j}: type={type(part).__name__}")
                if hasattr(part, "text") and part.text:
                    print(f"  text (first 200 chars): {part.text[:200]}")
                if hasattr(part, "thought") and part.thought:
                    print(f"  thought: True")

    print(f"\nusage: {response.usage_metadata}")


asyncio.run(main())