"""Semantic search service over indexed code."""

from dataclasses import dataclass

import asyncpg
import structlog

from src.core.embeddings import EmbeddingProvider

logger = structlog.get_logger()


@dataclass
class SearchResult:
    """A single search result."""

    chunk_name: str
    chunk_type: str
    file_path: str
    similarity: float
    content: str
    metadata: dict


class SearchService:
    """Searches indexed code via semantic similarity."""

    def __init__(
        self,
        embedder: EmbeddingProvider,
        db_host: str = "localhost",
        db_port: int = 5433,
        db_user: str = "mageaudit",
        db_password: str = "dev_password",
        db_name: str = "mage_audit",
    ) -> None:
        self._embedder = embedder
        self._db_config = {
            "host": db_host,
            "port": db_port,
            "user": db_user,
            "password": db_password,
            "database": db_name,
        }

    async def search(
        self,
        query: str,
        repo_name: str,
        limit: int = 5,
        min_similarity: float = 0.0,
    ) -> list[SearchResult]:
        """Search indexed code by semantic similarity.

        Args:
            query: Natural language search query.
            repo_name: Repository to search in.
            limit: Maximum number of results.
            min_similarity: Minimum similarity threshold (0.0-1.0).

        Returns:
            List of SearchResult sorted by similarity (highest first).
        """
        logger.info("Searching", query=query, repo=repo_name, limit=limit)

        query_embedding = self._embedder.embed([query])
        vector_str = "[" + ",".join(str(v) for v in query_embedding.vectors[0]) + "]"

        conn = await asyncpg.connect(**self._db_config)
        try:
            rows = await conn.fetch(
                """
                SELECT
                    chunk_name, chunk_type, file_path, content,
                    1 - (embedding <=> $1::vector) AS similarity,
                    metadata
                FROM code_chunks
                WHERE repo_name = $2
                ORDER BY embedding <=> $1::vector
                LIMIT $3
                """,
                vector_str,
                repo_name,
                limit,
            )
        finally:
            await conn.close()

        results = []
        for row in rows:
            sim = float(row["similarity"])
            if sim < min_similarity:
                continue

            meta = row["metadata"]
            if isinstance(meta, str):
                import json

                meta = json.loads(meta)

            results.append(
                SearchResult(
                    chunk_name=row["chunk_name"],
                    chunk_type=row["chunk_type"],
                    file_path=row["file_path"],
                    similarity=sim,
                    content=row["content"],
                    metadata=meta,
                )
            )

        logger.info("Search complete", results=len(results))
        return results
