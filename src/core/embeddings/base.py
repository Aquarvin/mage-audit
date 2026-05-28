"""Abstract base class for embedding providers."""

from abc import ABC, abstractmethod

from src.core.embeddings.types import EmbeddingResult


class EmbeddingProvider(ABC):
    """Abstract interface for embedding providers.

    Implementations: LocalEmbedder (sentence-transformers),
    GeminiEmbedder, OpenAIEmbedder, VoyageEmbedder.
    """

    def __init__(self, model: str, dimensions: int) -> None:
        self.model = model
        self.dimensions = dimensions

    @abstractmethod
    def embed(self, texts: list[str]) -> EmbeddingResult:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of strings to embed.

        Returns:
            EmbeddingResult with vectors and metadata.
        """
        ...
