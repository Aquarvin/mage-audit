"""API request/response schemas."""

from pydantic import BaseModel, Field

# --- Review ---


class ReviewRequest(BaseModel):
    """Request body for code review."""

    code: str = Field(..., description="PHP source code to review.")
    file_path: str = Field(default="unknown.php", description="File path for context.")
    repo_name: str | None = Field(
        default=None,
        description="Repository name for RAG mode. If omitted, uses simple mode.",
    )


class FindingResponse(BaseModel):
    """A single code review finding."""

    severity: str
    line: int | None = None
    category: str
    issue: str
    suggestion: str


class ReviewResponse(BaseModel):
    """Response from code review."""

    file_path: str
    mode: str = Field(description="'simple' or 'rag'")
    findings: list[FindingResponse]
    model: str
    input_tokens: int
    output_tokens: int
    findings_count: int


# --- Search ---


class SearchRequest(BaseModel):
    """Request body for semantic search."""

    query: str = Field(..., description="Natural language search query.")
    repo_name: str = Field(..., description="Repository to search in.")
    limit: int = Field(default=5, ge=1, le=20, description="Max results.")


class SearchResultResponse(BaseModel):
    """A single search result."""

    chunk_name: str
    chunk_type: str
    file_path: str
    similarity: float
    content: str
    tags: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    """Response from semantic search."""

    query: str
    repo_name: str
    results: list[SearchResultResponse]
    results_count: int
