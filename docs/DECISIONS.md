# Architectural Decision Records (ADRs)

This document records significant architectural decisions made during the development of Mage Audit. Each ADR follows a simple format: Context → Decision → Consequences.

---

## ADR-001: Layered architecture (core → languages → frameworks)

**Date**: 2026-05-17

**Status**: Accepted

### Context

Building yet another generic AI code reviewer would compete directly with established tools (CodeRabbit, Greptile, Cursor BugBot, Copilot). These tools are well-funded and have a head start.

However, none of them deeply understand framework-specific conventions. A Magento `Plugin` looks similar to a Symfony `EventSubscriber` in syntax but has completely different semantics and constraints.

### Decision

Build a layered system where:

1. **Core** is framework-agnostic AI infrastructure (LLM, embeddings, parsing, agents)
2. **Languages** is language-specific logic (PHP, later Python, JS)
3. **Frameworks** is framework-specific knowledge (Magento, later Symfony, Laravel)

This means ~80% of the codebase (Core + Languages) is reusable when adding a new framework.

### Consequences

**Positive:**
- Clear specialization moat for Magento
- Easy to extend to new frameworks
- Forces clean separation of concerns

**Negative:**
- More upfront design work
- More files and packages to manage
- Some logic might span layers awkwardly (we'll see)

---

## ADR-002: Provider abstraction for LLMs and Embeddings

**Date**: 2026-05-17

**Status**: Accepted

### Context

LLM landscape is changing rapidly. Models from different providers (OpenAI, Anthropic, Google, Meta) have different APIs, capabilities, and pricing. Locking into a single provider creates technical debt within months.

Additionally, the project needs to support free-tier development (Gemini, local Ollama) while being ready to swap to paid models (Claude, GPT-4) without code changes.

### Decision

Implement an abstract `LLMProvider` interface with concrete implementations per provider. Same pattern for `EmbeddingProvider`.

Switching providers requires only an environment variable change.

### Consequences

**Positive:**
- Easy provider comparison (critical for Phase 3 evaluation)
- Cost optimization through provider mixing
- Future-proof against provider changes

**Negative:**
- Common denominator API (loses provider-specific features)
- More code than directly calling provider SDKs
- Need to implement each provider's quirks separately

---

## ADR-003: PostgreSQL + pgvector instead of dedicated vector database

**Date**: 2026-05-17

**Status**: Accepted

### Context

Vector storage options include:
- Dedicated: Pinecone, Weaviate, Qdrant, Chroma
- Embedded: pgvector (PostgreSQL extension), sqlite-vec

Dedicated solutions offer specialized features. PostgreSQL with pgvector is "good enough" for most use cases.

### Decision

Use PostgreSQL + pgvector for the entire project lifecycle, unless and until performance becomes a documented bottleneck.

### Consequences

**Positive:**
- One database to operate (vs two)
- Free, open-source, runs locally
- Strong consistency, joins between vectors and relational data
- Wide ecosystem support

**Negative:**
- Lower top-end performance than specialized solutions
- Fewer specialized vector features (e.g., metadata filtering optimizations)
- Will need migration if scaling beyond ~10M vectors per repository