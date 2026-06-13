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
