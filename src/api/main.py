"""Mage Audit API — REST endpoints for code review and search."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException

from src.api.schemas import (
    FindingResponse,
    ReviewRequest,
    ReviewResponse,
    SearchRequest,
    SearchResponse,
    SearchResultResponse,
)
from src.core.config import settings

logger = structlog.get_logger()

# Global services — initialized on startup
_services = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup, clean up on shutdown."""
    logger.info("Starting Mage Audit API")

    # Lazy imports — only load heavy dependencies when API starts
    from src.core.agent import RAGReviewService, ReviewService, SearchService
    from src.core.embeddings import LocalEmbedder
    from src.core.llm import get_llm_provider

    embedder = LocalEmbedder()
    llm = get_llm_provider(settings.llm_provider)
    search_service = SearchService(embedder=embedder)

    _services["llm"] = llm
    _services["embedder"] = embedder
    _services["review"] = ReviewService(llm)
    _services["search"] = search_service
    _services["rag_review"] = RAGReviewService(llm=llm, search=search_service)

    logger.info(
        "Services initialized",
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
        embedding_model=embedder.model,
    )

    yield

    logger.info("Shutting down Mage Audit API")
    _services.clear()


app = FastAPI(
    title="Mage Audit API",
    description="AI-powered architecture auditor for Magento codebases",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "services": list(_services.keys()),
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
    }


@app.post("/api/v1/review", response_model=ReviewResponse)
async def review_code(request: ReviewRequest):
    """Review PHP code for bugs, security issues, and architecture problems.

    If `repo_name` is provided, uses RAG mode (searches indexed codebase for context).
    Otherwise, uses simple mode (sends code directly to LLM).
    """
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="Code cannot be empty.")

    try:
        if request.repo_name:
            # RAG mode
            service = _services["rag_review"]
            result = await service.review_file(
                request.file_path, request.code, repo_name=request.repo_name
            )
            mode = "rag"
        else:
            # Simple mode
            service = _services["review"]
            result = await service.review_file(request.file_path, request.code)
            mode = "simple"

    except Exception as e:
        logger.error("Review failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Review failed: {str(e)}")

    findings = [
        FindingResponse(
            severity=f.severity,
            line=f.line,
            category=f.category,
            issue=f.issue,
            suggestion=f.suggestion,
        )
        for f in result.findings
    ]

    return ReviewResponse(
        file_path=result.file_path,
        mode=mode,
        findings=findings,
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        findings_count=len(findings),
    )


@app.post("/api/v1/search", response_model=SearchResponse)
async def search_code(request: SearchRequest):
    """Search indexed code by semantic similarity."""
    try:
        service = _services["search"]
        results = await service.search(
            query=request.query,
            repo_name=request.repo_name,
            limit=request.limit,
        )
    except Exception as e:
        logger.error("Search failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

    response_results = []
    for r in results:
        tags = []
        deps = r.metadata.get("dependencies", [])
        tags = [d for d in deps if d.startswith("[")]

        response_results.append(
            SearchResultResponse(
                chunk_name=r.chunk_name,
                chunk_type=r.chunk_type,
                file_path=r.file_path,
                similarity=round(r.similarity, 4),
                content=r.content,
                tags=tags,
            )
        )

    return SearchResponse(
        query=request.query,
        repo_name=request.repo_name,
        results=response_results,
        results_count=len(response_results),
    )
