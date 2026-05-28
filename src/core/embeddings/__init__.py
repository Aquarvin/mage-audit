"""Embedding provider abstraction layer."""

from src.core.embeddings.base import EmbeddingProvider
from src.core.embeddings.local import LocalEmbedder
from src.core.embeddings.types import EmbeddingResult

__all__ = [
    "EmbeddingProvider",
    "EmbeddingResult",
    "LocalEmbedder",
]
