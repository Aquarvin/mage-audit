"""Evaluate Simple vs RAG review modes side by side."""

import asyncio
from pathlib import Path

from src.core.agent import RAGReviewService, ReviewService, SearchService
from src.core.config import settings
from src.core.embeddings import LocalEmbedder
from src.core.llm import get_llm_provider

TEST_FILE = Path("notebooks/samples/bad_module.php")
REPO_NAME = "vendor-order-manager"

# Known issues in bad_module.php (our "ground truth")
# As a Magento expert, YOU define what the correct findings are.
KNOWN_ISSUES = [
    {
        "id": "SQL_INJECTION",
        "severity": "critical",
        "description": "SQL injection in updateInventory via string concatenation",
    },
    {
        "id": "ABSTRACT_MODEL",
        "severity": "critical",
        "description": "Service class extends AbstractModel instead of being a plain class",
    },
    {
        "id": "MISSING_PARENT_CONSTRUCT",
        "severity": "error",
        "description": "Missing parent::__construct() call when extending AbstractModel",
    },
    {
        "id": "NO_TYPE_HINTS_CONSTRUCTOR",
        "severity": "error",
        "description": "Constructor parameters lack type hints",
    },
    {
        "id": "NO_TYPE_HINTS_METHODS",
        "severity": "warning",
        "description": "Method parameters/return types lack type hints",
    },
    {
        "id": "DIRECT_SQL",
        "severity": "critical",
        "description": "Direct SQL query bypasses Magento inventory API",
    },
    {
        "id": "ECHO_IN_SERVICE",
        "severity": "error",
        "description": "Direct echo output in service class",
    },
    {
        "id": "HARDCODED_STATUS",
        "severity": "warning",
        "description": "Hardcoded order status strings instead of constants",
    },
    {
        "id": "HARDCODED_DISCOUNT",
        "severity": "warning",
        "description": "Hardcoded discount threshold and rate",
    },
    {
        "id": "NO_ERROR_HANDLING",
        "severity": "error",
        "description": "No try-catch around repository operations",
    },
    {
        "id": "ALWAYS_RETURNS_TRUE",
        "severity": "warning",
        "description": "processOrder always returns true regardless of outcome",
    },
    {
        "id": "UNUSED_LOGGER",
        "severity": "warning",
        "description": "Logger injected but never used",
    },
    {
        "id": "NO_TRANSACTION",
        "severity": "warning",
        "description": "Multiple DB operations without transaction management",
    },
]


def match_finding_to_known(finding, known_issues) -> str | None:
    """Try to match a finding to a known issue by keywords."""
    text = (finding.issue + " " + finding.suggestion).lower()

    # Each value is a list of options. Each option is either:
    # - a string: must appear in text
    # - a tuple of strings: ALL must appear in text
    matchers = {
        "SQL_INJECTION": ["sql injection", "sql inject", "unsanitized", "concatenat"],
        "ABSTRACT_MODEL": [
            "abstractmodel",
            "abstract model",
            "extends abstractmodel",
            "service class",
        ],
        "MISSING_PARENT_CONSTRUCT": ["parent::__construct", "parent constructor"],
        "NO_TYPE_HINTS_CONSTRUCTOR": [
            ("type hint", "constructor"),
            ("constructor", "type"),
        ],
        "NO_TYPE_HINTS_METHODS": [
            ("type hint", "method"),
            ("type hint", "parameter"),
            "return type",
        ],
        "DIRECT_SQL": ["direct sql", "direct database", "bypass", "getresource"],
        "ECHO_IN_SERVICE": ["echo", "direct output"],
        "HARDCODED_STATUS": [
            ("hardcoded", "status"),
            ("magic string", "pending"),
            ("magic", "processing"),
        ],
        "HARDCODED_DISCOUNT": [
            ("hardcoded", "discount"),
            ("hardcoded", "1000"),
            "magic number",
        ],
        "NO_ERROR_HANDLING": ["try-catch", "try catch", "error handling", "exception"],
        "ALWAYS_RETURNS_TRUE": ["always return", "returns true", "return value"],
        "UNUSED_LOGGER": [
            ("logger", "never used"),
            ("logger", "unused"),
            ("logger", "not used"),
        ],
        "NO_TRANSACTION": ["transaction", "atomicity", "atomic"],
    }

    for issue_id, keywords in matchers.items():
        for kw in keywords:
            if isinstance(kw, tuple):
                # All words in tuple must be present
                if all(word in text for word in kw):
                    return issue_id
            elif isinstance(kw, str):
                if kw in text:
                    return issue_id

    return None


async def run_evaluation():
    code = TEST_FILE.read_text(encoding="utf-8")
    llm = get_llm_provider(settings.llm_provider)

    print("=" * 70)
    print("  EVALUATION: Simple vs RAG Code Review")
    print("=" * 70)
    print(f"\nFile: {TEST_FILE}")
    print(f"Known issues: {len(KNOWN_ISSUES)}")
    print(f"Model: {settings.llm_model}")

    # --- Run Simple mode ---
    print("\n--- Running Simple mode ---")
    simple_service = ReviewService(llm)
    simple_result = await simple_service.review_file(str(TEST_FILE), code)
    print(f"Simple findings: {len(simple_result.findings)}")

    # --- Run RAG mode ---
    print("\n--- Running RAG mode ---")
    embedder = LocalEmbedder()
    search = SearchService(embedder=embedder)
    rag_service = RAGReviewService(llm=llm, search=search)
    rag_result = await rag_service.review_file(
        str(TEST_FILE), code, repo_name=REPO_NAME
    )
    print(f"RAG findings: {len(rag_result.findings)}")

    # --- Match findings to known issues ---
    print("\n" + "=" * 70)
    print("  KNOWN ISSUE DETECTION")
    print("=" * 70)

    simple_matched = set()
    rag_matched = set()

    for f in simple_result.findings:
        match = match_finding_to_known(f, KNOWN_ISSUES)
        if match:
            simple_matched.add(match)

    for f in rag_result.findings:
        match = match_finding_to_known(f, KNOWN_ISSUES)
        if match:
            rag_matched.add(match)

    print(f"\n{'Known Issue':<30} {'Sev':<10} {'Simple':<10} {'RAG':<10}")
    print("-" * 60)

    for issue in KNOWN_ISSUES:
        s = "✓" if issue["id"] in simple_matched else "✗"
        r = "✓" if issue["id"] in rag_matched else "✗"
        print(f"{issue['id']:<30} {issue['severity']:<10} {s:<10} {r:<10}")

    simple_recall = len(simple_matched) / len(KNOWN_ISSUES)
    rag_recall = len(rag_matched) / len(KNOWN_ISSUES)

    print(
        f"\nSimple recall: {len(simple_matched)}/{len(KNOWN_ISSUES)} = {simple_recall:.0%}"
    )
    print(f"RAG recall:    {len(rag_matched)}/{len(KNOWN_ISSUES)} = {rag_recall:.0%}")

    # --- Project-specific references ---
    print("\n" + "=" * 70)
    print("  PROJECT-SPECIFIC REFERENCES")
    print("=" * 70)

    simple_refs = 0
    rag_refs = 0

    project_keywords = [
        "context",
        "consistent with",
        "from the context",
        "Vendor\\OrderManager",
        "vendor-order-manager",
        "project's pattern",
        "from the project",
    ]

    for f in simple_result.findings:
        text = f.issue + " " + f.suggestion
        if any(kw.lower() in text.lower() for kw in project_keywords):
            simple_refs += 1

    for f in rag_result.findings:
        text = f.issue + " " + f.suggestion
        if any(kw.lower() in text.lower() for kw in project_keywords):
            rag_refs += 1

    print(f"\nSimple: {simple_refs} findings reference project code")
    print(f"RAG:    {rag_refs} findings reference project code")

    # --- Token cost ---
    print("\n" + "=" * 70)
    print("  COST COMPARISON")
    print("=" * 70)
    print(f"\n{'Metric':<25} {'Simple':<15} {'RAG':<15}")
    print("-" * 55)
    print(
        f"{'Input tokens':<25} {simple_result.input_tokens:<15} {rag_result.input_tokens:<15}"
    )
    print(
        f"{'Output tokens':<25} {simple_result.output_tokens:<15} {rag_result.output_tokens:<15}"
    )
    total_s = simple_result.input_tokens + simple_result.output_tokens
    total_r = rag_result.input_tokens + rag_result.output_tokens
    print(f"{'Total tokens':<25} {total_s:<15} {total_r:<15}")
    print(
        f"{'Findings':<25} {len(simple_result.findings):<15} {len(rag_result.findings):<15}"
    )
    print(f"{'Project references':<25} {simple_refs:<15} {rag_refs:<15}")

    # --- Summary ---
    print("\n" + "=" * 70)
    print("  VERDICT")
    print("=" * 70)

    if rag_recall >= simple_recall and rag_refs > simple_refs:
        print(
            "\n✓ RAG mode is BETTER: equal or higher recall + project-specific advice"
        )
    elif rag_recall >= simple_recall:
        print("\n~ RAG mode is COMPARABLE: similar recall, check references manually")
    else:
        print(
            f"\n✗ RAG mode MISSED issues: recall {rag_recall:.0%} vs {simple_recall:.0%}"
        )
        missed = simple_matched - rag_matched
        if missed:
            print(f"  Missed by RAG: {missed}")

    print()


asyncio.run(run_evaluation())
