"""Index sample Magento module and search it."""

import asyncio

import asyncpg

from src.core.embeddings import LocalEmbedder
from src.frameworks.magento import MagentoModuleIndexer

MODULE_PATH = "notebooks/samples/sample-module"
REPO_NAME = "vendor-order-manager"


async def main():
    # Initialize
    print("Loading embedding model...")
    embedder = LocalEmbedder()

    indexer = MagentoModuleIndexer(embedder=embedder)

    # Index the module
    print(f"\n=== Indexing {MODULE_PATH} ===\n")
    stats = await indexer.index_module(MODULE_PATH, repo_name=REPO_NAME)

    print("\n--- Indexing Stats ---")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Search
    print("\n=== Semantic Search ===\n")
    conn = await asyncpg.connect(
        host="localhost",
        port=5433,
        user="mageaudit",
        password="dev_password",
        database="mage_audit",
    )

    queries = [
        "order processing logic",
        "event observer after order placement",
        "plugin that modifies save behavior",
        "discount calculation",
        "interface contract for order service",
    ]

    for query in queries:
        print(f"Query: '{query}'")

        query_embedding = embedder.embed([query])
        vector_str = "[" + ",".join(str(v) for v in query_embedding.vectors[0]) + "]"

        rows = await conn.fetch(
            """
            SELECT
                chunk_name, chunk_type, file_path,
                1 - (embedding <=> $1::vector) AS similarity,
                metadata
            FROM code_chunks
            WHERE repo_name = $2
            ORDER BY embedding <=> $1::vector
            LIMIT 3
            """,
            vector_str,
            REPO_NAME,
        )

        for row in rows:
            meta = row["metadata"]
            if isinstance(meta, str):
                import json as json_mod

                meta = json_mod.loads(meta)
            magento_tags = ""
            if "dependencies" in meta:
                tags = [d for d in meta["dependencies"] if d.startswith("[")]
                if tags:
                    magento_tags = " " + " ".join(tags)

            print(
                f"  {row['similarity']:.4f}  "
                f"{row['chunk_type']:8s} "
                f"{row['file_path']}::{row['chunk_name']}"
                f"{magento_tags}"
            )
        print()

    await conn.close()
    print("Done!")


asyncio.run(main())
