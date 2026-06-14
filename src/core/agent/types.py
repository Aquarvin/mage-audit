"""Domain types for code review results."""

from enum import StrEnum

from pydantic import BaseModel


class Severity(StrEnum):
    """Severity level of a code review finding."""

    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Category(StrEnum):
    """Category of a code review finding."""

    SECURITY = "security"
    BUG = "bug"
    ARCHITECTURE = "architecture"
    PERFORMANCE = "performance"
    STYLE = "style"


class Finding(BaseModel):
    """A single code review finding."""

    severity: Severity
    line: int | None = None
    category: Category
    issue: str
    suggestion: str

    @classmethod
    def from_llm_output(cls, data: dict) -> "Finding":
        """Create Finding from LLM output with fallback mapping.

        Handles common LLM mistakes:
        - severity contains a category value → map to default severity
        - category contains a severity value → map to default category
        - missing fields → use defaults
        """
        severity_raw = str(data.get("severity", "warning")).lower()
        category_raw = str(data.get("category", "architecture")).lower()

        # If severity contains a category value, fix it
        category_values = {s.value for s in Category}
        severity_values = {s.value for s in Severity}

        if severity_raw in category_values and severity_raw not in severity_values:
            # Gemini put category in severity field — use "warning" as default
            severity_raw = "warning"

        if category_raw in severity_values and category_raw not in category_values:
            # Gemini put severity in category field — use "architecture" as default
            category_raw = "architecture"

        # Clamp to valid values
        if severity_raw not in severity_values:
            severity_raw = "warning"
        if category_raw not in category_values:
            category_raw = "architecture"

        return cls(
            severity=Severity(severity_raw),
            line=data.get("line"),
            category=Category(category_raw),
            issue=data.get("issue", "No description"),
            suggestion=data.get("suggestion", "No suggestion"),
        )


class ReviewResult(BaseModel):
    """Complete result of a code review."""

    file_path: str
    findings: list[Finding]
    model: str
    input_tokens: int
    output_tokens: int

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.WARNING)
