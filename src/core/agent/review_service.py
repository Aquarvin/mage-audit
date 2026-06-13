"""Code review service — orchestrates LLM calls for code analysis."""

import json

import structlog

from src.core.agent.types import Finding, ReviewResult
from src.core.llm import LLMMessage, LLMProvider, Role

logger = structlog.get_logger()

SYSTEM_PROMPT = """\
You are a senior PHP / Magento 2 (Adobe Commerce) developer \
performing a thorough code review.

Analyze the provided code and return your findings as a JSON array.
Each finding must have exactly these fields:
- severity: one of "critical", "error", "warning", "info"
- line: approximate line number (integer or null if not applicable)
- category: one of "security", "bug", "architecture", "performance", "style"
- issue: one-line description of the problem
- suggestion: concrete suggestion how to fix it

Rules:
- Be specific. Mention exact variable names, method names, class names.
- Focus on real problems, not nitpicks.
- For Magento code: check for proper use of dependency injection, \
service contracts, plugins, observers, and resource models.
- Flag any direct SQL queries, missing type hints, hardcoded values, \
and violations of Magento architecture.

Return ONLY a valid JSON array. No markdown, no explanation, no preamble.\
"""


class ReviewService:
    """Performs AI-powered code review using an LLM provider."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def review_file(self, file_path: str, code: str) -> ReviewResult:
        """Review a single file and return structured findings.

        Args:
            file_path: Path to the file (for display purposes).
            code: The source code to review.

        Returns:
            ReviewResult with parsed findings.
        """
        logger.info("Starting review", file=file_path, code_length=len(code))

        messages = [
            LLMMessage(role=Role.SYSTEM, content=SYSTEM_PROMPT),
            LLMMessage(
                role=Role.USER,
                content=f"Review this code from `{file_path}`:\n\n```php\n{code}\n```",
            ),
        ]

        response = await self._llm.complete(messages, temperature=0.3)

        logger.info(
            "LLM response received",
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        findings = self._parse_findings(response.content)

        logger.info("Review complete", findings_count=len(findings))

        return ReviewResult(
            file_path=file_path,
            findings=findings,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    def _parse_findings(self, raw: str) -> list[Finding]:
        """Parse LLM output into structured findings.

        Handles common LLM quirks: markdown fences, extra text, etc.
        """
        text = raw.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            # Remove first line (```json or ```)
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3].strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM output as JSON", error=str(e))
            logger.debug("Raw output", raw=raw[:500])
            return []

        if not isinstance(data, list):
            logger.error("LLM output is not a JSON array", type=type(data).__name__)
            return []

        findings = []
        for item in data:
            try:
                findings.append(Finding.model_validate(item))
            except Exception as e:
                logger.warning("Skipping invalid finding", error=str(e), item=item)
                continue

        return findings
