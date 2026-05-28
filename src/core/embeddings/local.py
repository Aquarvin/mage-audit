"""Local embedding provider using sentence-transformers."""

from sentence_transformers import SentenceTransformer

from src.core.embeddings.base import EmbeddingProvider
from src.core.embeddings.types import EmbeddingResult


class LocalEmbedder(EmbeddingProvider):
    """Embedding provider using local sentence-transformers models.

    Runs on CPU or GPU. No API calls, no cost, no rate limits.
    """

    def __init__(self, model: str = "BAAI/bge-small-en-v1.5") -> None:
        self._model = SentenceTransformer(model)
        dims = self._model.get_embedding_dimension()
        super().__init__(model=model, dimensions=dims)

    def embed(self, texts: list[str]) -> EmbeddingResult:
        """Generate embeddings locally via sentence-transformers."""
        vectors = self._model.encode(texts)
        return EmbeddingResult(
            vectors=vectors.tolist(),
            model=self.model,
            dimensions=self.dimensions,
        )
