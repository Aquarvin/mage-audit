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
        """Parse LLM output into structured findings."""
        text = raw.strip()

        # Strip markdown code fences
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3].strip()

        # Fix unescaped backslashes by walking character by character
        text = self._fix_json_backslashes(text)

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM output as JSON", error=str(e))
            logger.debug("Raw output", raw=raw[:500])
            return []

        if not isinstance(data, list):
            logger.error("LLM output is not a JSON array")
            return []

        findings = []
        for item in data:
            try:
                findings.append(Finding.model_validate(item))
            except Exception as e:
                logger.warning("Skipping invalid finding", error=str(e))

        return findings

    @staticmethod
    def _fix_json_backslashes(text: str) -> str:
        """Fix unescaped backslashes in LLM-generated JSON.

        LLMs often produce PHP namespaces like \\Magento\\Sales with
        inconsistent escaping. This method walks the string character
        by character and ensures every backslash is properly escaped.
        """
        result = []
        i = 0
        while i < len(text):
            if text[i] == "\\" and i + 1 < len(text):
                next_char = text[i + 1]
                if next_char in '"\\//bfnrt':
                    # Valid JSON escape: \", \\, \/, \b, \f, \n, \r, \t
                    result.append(text[i : i + 2])
                    i += 2
                elif (
                    next_char == "u"
                    and i + 5 < len(text)
                    and all(c in "0123456789abcdefABCDEF" for c in text[i + 2 : i + 6])
                ):
                    # Valid unicode escape: \uXXXX
                    result.append(text[i : i + 6])
                    i += 6
                else:
                    # Invalid escape: add extra backslash
                    result.append("\\\\")
                    i += 1
            else:
                result.append(text[i])
                i += 1
        return "".join(result)
