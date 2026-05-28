"""Domain types for embedding operations."""

from pydantic import BaseModel


class EmbeddingResult(BaseModel):
    """Result of embedding one or more texts."""

    vectors: list[list[float]]
    model: str
    dimensions: int
    token_count: int | None = None
