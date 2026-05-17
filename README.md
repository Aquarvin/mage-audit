# Mage Audit

**AI-powered architecture auditor for Magento codebases.**

Most AI code review tools (CodeRabbit, Greptile, Copilot) treat code as generic text. They don't understand the architectural conventions of complex frameworks like Magento — observers, plugins, dependency injection, layout XML, area-scoped configuration.

Mage Audit is built differently. It combines a universal AI code analysis engine with framework-specific knowledge layers, starting with Magento 2.

## Status

🚧 **Phase 0 — Foundation.** This project is under active development as part of a structured journey into AI engineering. See [docs/ROADMAP.md](docs/ROADMAP.md) for the full plan.

## Architecture

Mage Audit is structured as a layered system:

- **Core (`src/core/`)** — Universal AI engine: LLM providers, embeddings, AST parsing, agent orchestration. Framework-agnostic.
- **Languages (`src/languages/`)** — Language-specific knowledge (PHP first).
- **Frameworks (`src/frameworks/`)** — Framework-specific knowledge (Magento first; Symfony, Laravel planned).

This layering means adding a new framework reuses 80% of the codebase.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for details.

## Tech Stack

- **Python 3.12** with `uv` for dependency management
- **FastAPI** for the HTTP API
- **PostgreSQL 16 + pgvector** for vector storage
- **Redis** for caching and job queues
- **tree-sitter** for AST-based code analysis
- **sentence-transformers** for local embeddings
- **Google Gemini, Anthropic Claude, local Ollama** as interchangeable LLM providers

## Quick Start

> ⚠️ Not yet runnable. Phase 0 in progress.

```bash
git clone https://github.com/Aquarvin/mage-audit.git
cd mage-audit
uv sync
docker compose up -d
uv run mage-audit review --file path/to/Module.php
```

## License

MIT — see [LICENSE](LICENSE).