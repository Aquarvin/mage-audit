"""RAG-powered code review service.

Retrieves relevant context from indexed codebase before sending to LLM.
This is the core innovation: review with project context, not in a vacuum.
"""

import json

import structlog

from src.core.agent.search_service import SearchService
from src.core.agent.types import Finding, ReviewResult
from src.core.llm import LLMMessage, LLMProvider, Role

logger = structlog.get_logger()

SYSTEM_PROMPT = """\
You are a senior PHP / Magento 2 (Adobe Commerce) developer \
performing a thorough code review.

You will receive:
1. The PHP file to review.
2. CONTEXT: related code from the same project (similar functions, \
classes that interact with the code being reviewed, relevant patterns).
3. MAGENTO CONFIG: information about how this code is registered \
in the Magento system (plugins, observers, preferences from di.xml/events.xml).

Use the context to make your review MORE SPECIFIC:
- If similar functions in the project follow a pattern, and the reviewed \
code breaks that pattern — flag it.
- If the code is registered as a plugin in di.xml, verify it has the \
correct before/after/around methods.
- If the code is an observer, verify it implements ObserverInterface \
and has an execute(Observer $observer) method.
- If there's a preference for an interface, verify all interface methods \
are implemented.

Return your findings as a JSON array.
Each finding must have exactly these fields:
- severity: one of "critical", "error", "warning", "info"
- line: approximate line number (integer or null)
- category: one of "security", "bug", "architecture", "performance", "style"
- issue: one-line description of the problem
- suggestion: concrete suggestion how to fix it

Rules:
- Be specific. Mention exact variable names, method names, class names.
- Focus on real problems, not nitpicks.
- Use the provided context to give project-specific advice, not generic.
- If the context shows a better pattern used elsewhere in the project, \
reference it in your suggestion.

Return ONLY a valid JSON array. No markdown, no explanation, no preamble.\
"""


class RAGReviewService:
    """Code review service enhanced with RAG — retrieves project context first."""

    def __init__(
        self,
        llm: LLMProvider,
        search: SearchService,
        context_chunks: int = 5,
        min_similarity: float = 0.4,
    ) -> None:
        self._llm = llm
        self._search = search
        self._context_chunks = context_chunks
        self._min_similarity = min_similarity

    async def review_file(
        self,
        file_path: str,
        code: str,
        repo_name: str,
    ) -> ReviewResult:
        """Review a file with RAG — retrieve context, then analyze.

        Args:
            file_path: Path to the file being reviewed.
            code: Source code of the file.
            repo_name: Repository name to search for context.

        Returns:
            ReviewResult with findings informed by project context.
        """
        # Step 1: Retrieve relevant context
        logger.info("RAG: retrieving context", file=file_path, repo=repo_name)

        context_text = await self._build_context(code, repo_name, file_path)

        # Step 2: Build messages with context
        user_content = self._build_user_message(file_path, code, context_text)

        messages = [
            LLMMessage(role=Role.SYSTEM, content=SYSTEM_PROMPT),
            LLMMessage(role=Role.USER, content=user_content),
        ]

        # Step 3: Call LLM
        logger.info("RAG: calling LLM", file=file_path)
        response = await self._llm.complete(messages, temperature=0.3)

        logger.info(
            "RAG: LLM response received",
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        # Step 4: Parse findings
        findings = self._parse_findings(response.content)

        return ReviewResult(
            file_path=file_path,
            findings=findings,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    async def _build_context(self, code: str, repo_name: str, file_path: str) -> str:
        """Search for relevant context using multiple strategies."""
        all_results = []
        seen_keys = set()

        # Strategy 1: Search by code content (first 300 chars)
        code_query = code[:300]
        results = await self._search.search(
            query=code_query,
            repo_name=repo_name,
            limit=3,
            min_similarity=self._min_similarity,
        )
        for r in results:
            key = f"{r.file_path}::{r.chunk_name}"
            if key not in seen_keys:
                seen_keys.add(key)
                all_results.append(r)

        # Strategy 2: Search by class/function names extracted from code
        names_query = self._extract_names_for_search(code)
        if names_query:
            results = await self._search.search(
                query=names_query,
                repo_name=repo_name,
                limit=3,
                min_similarity=self._min_similarity,
            )
            for r in results:
                key = f"{r.file_path}::{r.chunk_name}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_results.append(r)

        # Strategy 3: Search by imports/dependencies
        deps_query = self._extract_deps_for_search(code)
        if deps_query:
            results = await self._search.search(
                query=deps_query,
                repo_name=repo_name,
                limit=3,
                min_similarity=self._min_similarity,
            )
            for r in results:
                key = f"{r.file_path}::{r.chunk_name}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_results.append(r)

        # Filter out chunks from the same file
        all_results = [r for r in all_results if r.file_path != file_path]

        # Sort by similarity and take top N
        all_results.sort(key=lambda r: r.similarity, reverse=True)
        all_results = all_results[: self._context_chunks]

        if not all_results:
            logger.info("RAG: no relevant context found", file=file_path)
            return ""

        logger.info(
            "RAG: context retrieved",
            chunks=len(all_results),
            strategies_used=len(
                [q for q in [code_query, names_query, deps_query] if q]
            ),
            top_similarity=f"{all_results[0].similarity:.4f}",
        )

        # Format context for LLM
        parts = ["## CONTEXT: Related code from this project\n"]
        for r in all_results:
            tags = ""
            deps = r.metadata.get("dependencies", [])
            magento_tags = [d for d in deps if d.startswith("[")]
            if magento_tags:
                tags = " " + " ".join(magento_tags)

            parts.append(
                f"### {r.file_path} :: {r.chunk_name} "
                f"({r.chunk_type}, similarity: {r.similarity:.2f}){tags}\n"
                f"```php\n{r.content}\n```\n"
            )

        return "\n".join(parts)

    @staticmethod
    def _extract_names_for_search(code: str) -> str:
        """Extract class and method names from code for search query."""
        import re

        names = []

        # Find class name
        match = re.search(r"class\s+(\w+)", code)
        if match:
            names.append(match.group(1))

        # Find method names
        for match in re.finditer(r"function\s+(\w+)", code):
            name = match.group(1)
            if name != "__construct":
                names.append(name)

        return " ".join(names) if names else ""

    @staticmethod
    def _extract_deps_for_search(code: str) -> str:
        """Extract use statements / dependencies for search query."""
        import re

        deps = []
        for match in re.finditer(r"use\s+([\w\\]+);", code):
            # Take last part of namespace
            full = match.group(1)
            short = full.split("\\")[-1]
            deps.append(short)

        return " ".join(deps[:5]) if deps else ""

    def _build_user_message(self, file_path: str, code: str, context: str) -> str:
        """Build the user message with file + context."""
        parts = []

        if context:
            parts.append(context)
            parts.append("---\n")

        parts.append(f"## FILE TO REVIEW: {file_path}\n\n```php\n{code}\n```")

        return "\n".join(parts)

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
                findings.append(Finding.from_llm_output(item))
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
