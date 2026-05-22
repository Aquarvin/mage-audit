"""Gemini LLM provider implementation."""

from collections.abc import AsyncIterator

from google import genai
from google.genai.types import Content, GenerateContentConfig, Part
from pydantic import BaseModel

from src.core.config import settings
from src.core.llm.base import LLMProvider
from src.core.llm.types import LLMMessage, LLMResponse, Role, TokenUsage


class GeminiProvider(LLMProvider):
    """Google Gemini provider via google-genai SDK."""

    def __init__(self, model: str = "") -> None:
        super().__init__(model or settings.llm_model)
        self._client = genai.Client(api_key=settings.google_api_key)

    def _convert_messages(
        self, messages: list[LLMMessage]
    ) -> tuple[str | None, list[Content]]:
        """Convert our LLMMessage format to Gemini's format.

        Gemini separates system instruction from conversation history.
        Returns (system_instruction, contents).
        """
        system_instruction = None
        contents = []

        for msg in messages:
            if msg.role == Role.SYSTEM:
                system_instruction = msg.content
            else:
                # Gemini uses "user" and "model" (not "assistant")
                role = "user" if msg.role == Role.USER else "model"
                contents.append(Content(role=role, parts=[Part(text=msg.content)]))

        return system_instruction, contents

    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        response_schema: type[BaseModel] | None = None,
    ) -> LLMResponse:
        """Generate completion via Gemini API."""
        system_instruction, contents = self._convert_messages(messages)

        config = GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
        )

        if response_schema is not None:
            config.response_mime_type = "application/json"
            config.response_schema = response_schema

        response = await self._client.aio.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )

        usage = response.usage_metadata
        return LLMResponse(
            content=response.text or "",
            model=self.model,
            usage=TokenUsage(
                input_tokens=usage.prompt_token_count or 0,
                output_tokens=usage.candidates_token_count or 0,
                thinking_tokens=usage.thoughts_token_count or 0,
            ),
            finish_reason=str(response.candidates[0].finish_reason)
            if response.candidates
            else None,
        )

    async def stream(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream completion token by token via Gemini API."""
        system_instruction, contents = self._convert_messages(messages)

        config = GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
        )

        response_stream = await self._client.aio.models.generate_content_stream(
            model=self.model,
            contents=contents,
            config=config,
        )

        async for chunk in response_stream:
            if chunk.text:
                yield chunk.text
