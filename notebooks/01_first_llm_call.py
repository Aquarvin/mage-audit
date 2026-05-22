"""
Day 3: First LLM API call — understanding the basics.
This is a learning script, not production code.
"""

import asyncio

from google import genai

from src.core.config import settings


async def main():
    client = genai.Client(api_key=settings.google_api_key)

    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents="Скажи одним предложением, что такое code review.",
    )

    print("=== Response ===")
    print(response.text)
    print()
    print("=== Metadata ===")
    print(f"Model: {response.model_version}")
    print(f"Finish reason: {response.candidates[0].finish_reason}")
    print(f"Token usage: {response.usage_metadata}")


asyncio.run(main())
