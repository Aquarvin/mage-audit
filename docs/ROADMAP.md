# Roadmap

## Status: Phase 0 — Foundation 🚧

| Phase   | Status        | Duration    | Description                |
| ------- | ------------- | ----------- | -------------------------- |
| Phase 0 | ✅ Complete    | Week 1      | Foundation setup           |
| Phase 1 | 🚧 In progress | Weeks 2-3   | Magento Knowledge Layer    |
| Phase 2 | 📋 Planned     | Weeks 4-6   | RAG Pipeline & Working MVP |
| Phase 3 | 📋 Planned     | Weeks 7-9   | Evaluation Framework       |
| Phase 4 | 📋 Planned     | Weeks 10-13 | Production-Ready Service   |
| Phase 5 | 📋 Planned     | Weeks 14-18 | Advanced Features          |
| Phase 6 | 📋 Planned     | Weeks 19-21 | Portfolio & Job Search     |

## Phase 0: Foundation (Week 1)

**Goal**: Working CLI prototype that reviews PHP files via Gemini API.

- [x] Day 1: Repository structure and documentation
- [x] Day 2: Local dev environment (Docker, Postgres, Redis)
- [x] Day 3: First LLM API integration (Gemini)
- [x] Day 4: LLM Provider abstraction
- [x] Day 5: Embeddings and vector store basics
- [x] Day 6-7: First working CLI prototype + CI

## Phase 1: Magento Knowledge Layer (Weeks 2-3) 🚧

- [x] Day 1: Tree-sitter PHP parsing and AST extraction
- [x] Day 2: Magento config parsers (di.xml, events.xml, module.xml)
- [x] Day 3: Module indexer (PHP + config → embeddings → pgvector)
- [x] Day 4: CLI commands — index and search with Magento tags
- [x] Day 5: Index real Magento module
- [ ] Day 6-7: Search API endpoint + demo video

## Phase 2: RAG Pipeline & MVP (Weeks 4-6) 🚧

- [x] Day 1: RAG Review Service — search + LLM review with project context
- [x] Day 2: Multi-strategy retrieval + fallback parsing (0 lost findings)
- [x] Day 3: RAG evaluation — compare Simple vs RAG quality

## Phase 3: Evaluation Framework (Weeks 7-9)

Will be detailed when Phase 2 completes.