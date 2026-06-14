"""Magento module indexer.

Walks a module directory, extracts PHP chunks and Magento config,
generates embeddings, and stores everything in pgvector.
"""

import json
import uuid
from pathlib import Path

import asyncpg
import structlog

from src.core.embeddings import EmbeddingProvider
from src.frameworks.magento.config_parser import MagentoConfigParser
from src.frameworks.magento.types import MagentoModuleConfig
from src.languages.php import CodeChunk, PHPExtractor

logger = structlog.get_logger()


class MagentoModuleIndexer:
    """Indexes a Magento module: PHP code + XML config → embeddings → pgvector."""

    def __init__(
        self,
        embedder: EmbeddingProvider,
        db_url: str = "postgresql://mageaudit:dev_password@localhost:5433/mage_audit",
    ) -> None:
        self._embedder = embedder
        self._db_url = db_url
        self._php_extractor = PHPExtractor()
        self._config_parser = MagentoConfigParser()

    async def index_module(self, module_path: str | Path, repo_name: str) -> dict:
        """Index an entire Magento module.

        Args:
            module_path: Path to the module root directory.
            repo_name: Name to identify this module in the database.

        Returns:
            Dictionary with indexing statistics.
        """
        module_path = Path(module_path)
        logger.info("Indexing module", path=str(module_path), repo=repo_name)

        # Step 1: Parse Magento config
        config = self._config_parser.parse_module_directory(module_path)

        # Step 2: Extract PHP chunks
        php_chunks = self._extract_php_files(module_path)

        # Step 3: Enrich chunks with Magento context
        enriched_chunks = self._enrich_with_config(php_chunks, config)

        # Step 4: Generate embeddings
        if not enriched_chunks:
            logger.warning("No chunks to index", path=str(module_path))
            return {"chunks": 0, "php_files": 0}

        texts_for_embedding = [
            self._chunk_to_embedding_text(c) for c in enriched_chunks
        ]
        logger.info("Generating embeddings", chunks=len(texts_for_embedding))
        embedding_result = self._embedder.embed(texts_for_embedding)

        # Step 5: Store in pgvector
        conn = await asyncpg.connect(self._db_url)
        try:
            # Clear old data for this repo
            deleted = await conn.execute(
                "DELETE FROM code_chunks WHERE repo_name = $1", repo_name
            )
            logger.info("Cleared old data", repo=repo_name, deleted=deleted)

            # Insert new chunks
            for i, chunk in enumerate(enriched_chunks):
                vector_str = (
                    "[" + ",".join(str(v) for v in embedding_result.vectors[i]) + "]"
                )
                await conn.execute(
                    """
                    INSERT INTO code_chunks
                        (id, repo_name, file_path, chunk_type, chunk_name, content, embedding, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7::vector, $8::jsonb)
                    """,  # noqa: E501
                    uuid.uuid4(),
                    repo_name,
                    chunk.file_path,
                    chunk.chunk_type,
                    chunk.name,
                    chunk.content,
                    vector_str,
                    json.dumps(self._chunk_metadata(chunk, config)),
                )

            count = await conn.fetchval(
                "SELECT COUNT(*) FROM code_chunks WHERE repo_name = $1", repo_name
            )
            logger.info("Indexing complete", repo=repo_name, total_chunks=count)

        finally:
            await conn.close()

        php_files = len(set(c.file_path for c in php_chunks))
        return {
            "repo_name": repo_name,
            "module_name": config.module_info.name if config.module_info else "unknown",
            "php_files": php_files,
            "chunks": len(enriched_chunks),
            "plugins": len(config.plugins),
            "observers": len(config.observers),
            "preferences": len(config.preferences),
        }

    def _extract_php_files(self, module_path: Path) -> list[CodeChunk]:
        """Walk module directory and extract PHP chunks from all .php files."""
        all_chunks = []
        php_files = sorted(module_path.rglob("*.php"))

        for php_file in php_files:
            relative_path = str(php_file.relative_to(module_path))
            try:
                code = php_file.read_text(encoding="utf-8")
                chunks = self._php_extractor.extract(code, file_path=relative_path)
                all_chunks.extend(chunks)
                logger.debug(
                    "Extracted PHP file",
                    file=relative_path,
                    chunks=len(chunks),
                )
            except Exception as e:
                logger.error(
                    "Failed to extract PHP file", file=relative_path, error=str(e)
                )

        logger.info(
            "PHP extraction complete", files=len(php_files), chunks=len(all_chunks)
        )
        return all_chunks

    def _enrich_with_config(
        self, chunks: list[CodeChunk], config: MagentoModuleConfig
    ) -> list[CodeChunk]:
        """Enrich PHP chunks with Magento config context.

        Adds metadata about plugins, observers, preferences to relevant chunks.
        """
        # Build lookup maps from config
        plugin_classes = {p.plugin_class: p for p in config.plugins}
        observer_classes = {o.instance_class: o for o in config.observers}
        preference_impls = {p.implementation: p for p in config.preferences}

        for chunk in chunks:
            if chunk.namespace and chunk.class_name:
                fqn = f"{chunk.namespace}\\{chunk.class_name}"
            elif chunk.namespace and chunk.chunk_type in (
                "class",
                "interface",
                "trait",
            ):
                fqn = f"{chunk.namespace}\\{chunk.name}"
            else:
                continue

            # Check if this class is a plugin
            if fqn in plugin_classes:
                plugin = plugin_classes[fqn]
                chunk.dependencies.append(f"[PLUGIN for {plugin.target_class}]")

            # Check if this class is an observer
            if fqn in observer_classes:
                obs = observer_classes[fqn]
                chunk.dependencies.append(f"[OBSERVER for {obs.event_name}]")

            # Check if this class is a preference implementation
            if fqn in preference_impls:
                pref = preference_impls[fqn]
                chunk.dependencies.append(f"[IMPLEMENTS {pref.interface}]")

        return chunks

    def _chunk_to_embedding_text(self, chunk: CodeChunk) -> str:
        """Convert a chunk to text optimized for embedding.

        Includes context beyond just the code: class name, file path,
        Magento annotations from config.
        """
        parts = []

        # Add context header
        if chunk.class_name and chunk.chunk_type == "method":
            parts.append(f"Method {chunk.class_name}::{chunk.name}")
        elif chunk.chunk_type == "class":
            parts.append(f"Class {chunk.name}")
        elif chunk.chunk_type == "interface":
            parts.append(f"Interface {chunk.name}")
        else:
            parts.append(f"{chunk.chunk_type} {chunk.name}")

        parts.append(f"File: {chunk.file_path}")

        # Add Magento context from enrichment
        for dep in chunk.dependencies:
            if dep.startswith("["):
                parts.append(dep)

        # Add the code itself
        parts.append(chunk.content)

        return "\n".join(parts)

    def _chunk_metadata(self, chunk: CodeChunk, config: MagentoModuleConfig) -> dict:
        """Build metadata JSON for a chunk."""
        meta = {
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "namespace": chunk.namespace,
        }
        if chunk.visibility:
            meta["visibility"] = chunk.visibility
        if chunk.class_name:
            meta["class_name"] = chunk.class_name
        if chunk.dependencies:
            meta["dependencies"] = chunk.dependencies
        if config.module_info:
            meta["module_name"] = config.module_info.name
        return meta
