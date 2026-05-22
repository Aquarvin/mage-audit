"""
Day 3: Code review experiments.
Testing different prompts to see how LLM quality changes.
"""

import asyncio
from pathlib import Path

from google import genai

from src.core.config import settings

SAMPLE_FILE = Path("notebooks/samples/bad_module.php")


async def review_simple(client, code: str) -> str:
    """Experiment 1: Simplest possible prompt."""
    response = await client.aio.models.generate_content(
        model=settings.llm_model,
        contents=f"Do a code review of this PHP code:\n\n```php\n{code}\n```",
    )
    return response.text


async def review_with_role(client, code: str) -> str:
    """Experiment 2: With system-like role in the prompt."""
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
    return response.text


async def review_structured(client, code: str) -> str:
    """Experiment 3: Requesting structured JSON output."""
    response = await client.aio.models.generate_content(
        model=settings.llm_model,
        contents=(
            "You are a senior Magento 2 developer performing a code review.\n\n"
            "Analyze the following PHP code and return your findings as a JSON array.\n"
            "Each finding must have these fields:\n"
            "- severity: 'critical', 'error', 'warning', or 'info'\n"
            "- line: approximate line number\n"
            "- category: 'security', 'bug', 'architecture', 'performance', 'style'\n"
            "- issue: one-line description of the problem\n"
            "- suggestion: how to fix it\n\n"
            "Return ONLY valid JSON, no markdown, no explanation.\n\n"
            f"```php\n{code}\n```"
        ),
    )
    return response.text


async def review_with_examples(client, code: str) -> str:
    """Experiment 4: Few-shot — giving an example of good review."""
    response = await client.aio.models.generate_content(
        model=settings.llm_model,
        contents=(
            "You are a senior Magento 2 developer performing a code review.\n\n"
            "Here is an example of how a good review finding looks:\n\n"
            "```json\n"
            "{\n"
            '  "severity": "critical",\n'
            '  "line": 15,\n'
            '  "category": "security",\n'
            '  "issue": "SQL injection via unsanitized user input in direct query",\n'
            '  "suggestion": "Use parameterized queries via $connection->quoteInto() '
            'or use Repository/Resource Model pattern"\n'
            "}\n"
            "```\n\n"
            "Now review this code. Return a JSON array of findings, "
            "ordered by severity (critical first). "
            "Return ONLY valid JSON.\n\n"
            f"```php\n{code}\n```"
        ),
    )
    return response.text


async def main():
    client = genai.Client(api_key=settings.google_api_key)
    code = SAMPLE_FILE.read_text(encoding="utf-8")

    experiments = [
        ("1. Simple prompt", review_simple),
        ("2. With role", review_with_role),
        ("3. Structured JSON", review_structured),
        ("4. Few-shot example", review_with_examples),
    ]

    for name, func in experiments:
        print(f"\n{'=' * 60}")
        print(f"  {name}")
        print(f"{'=' * 60}\n")

        result = await func(client, code)
        print(result)
        print()

        # Small delay to avoid rate limiting
        await asyncio.sleep(2)


asyncio.run(main())
