# Roadmap

## Current Status: Phase 2 Complete ✅

| Phase   | Status     | Description                                                              |
| ------- | ---------- | ------------------------------------------------------------------------ |
| Phase 0 | ✅ Complete | Foundation: repo, Docker, FastAPI, LLM abstraction, embeddings, CLI      |
| Phase 1 | ✅ Complete | Magento Knowledge Layer: tree-sitter, config parser, module indexer      |
| Phase 2 | ✅ Complete | RAG Pipeline: context-aware review, multi-strategy retrieval, evaluation |
| Phase 3 | 📋 Planned  | Production-Ready Service: GitHub App, multi-tenancy, monitoring          |
| Phase 4 | 📋 Planned  | Advanced Features: fine-tuning, multi-agent, self-improvement            |
| Phase 5 | 📋 Planned  | Portfolio Packaging: blog posts, demo video, job applications            |

## Phase 0: Foundation ✅

- [x] Repository structure with layered architecture
- [x] Docker Compose (PostgreSQL + pgvector, Redis)
- [x] FastAPI with /health endpoint
- [x] LLM Provider abstraction (Gemini implemented)
- [x] Embedding Provider abstraction (local BGE-small)
- [x] First working CLI prototype
- [x] GitHub Actions CI

## Phase 1: Magento Knowledge Layer ✅

- [x] Tree-sitter PHP parsing and AST extraction
- [x] PHPExtractor: classes, methods, functions with metadata
- [x] Magento config parsers (di.xml, events.xml, module.xml)
- [x] Module indexer: PHP + config → embeddings → pgvector
- [x] CLI commands: index and search
- [x] Tested on real Magento module (TestHobby, 37 chunks)

## Phase 2: RAG Pipeline ✅

- [x] RAG Review Service: search + LLM review with project context
- [x] Multi-strategy retrieval (code content + names + dependencies)
- [x] Fallback parsing for LLM output (zero findings lost)
- [x] Evaluation: RAG recall 69% vs Simple 54% on 13 known issues
- [x] 10x more project-specific references in RAG mode

## Phase 3: Production-Ready Service (planned)

- [ ] GitHub App / webhook integration
- [ ] Async job processing for large PRs
- [ ] Multi-tenancy and cost tracking
- [ ] Web UI dashboard
- [ ] Monitoring and observability

## Phase 4: Advanced Features (planned)

- [ ] Fine-tuning on Magento-specific code review data
- [ ] Multi-agent architecture (security, performance, architecture agents)
- [ ] Hybrid search (BM25 + embeddings)
- [ ] Reranking with cross-encoder