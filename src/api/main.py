from contextlib import asynccontextmanager

import redis.asyncio as aioredis
import structlog
from fastapi import FastAPI
from sqlalchemy import text

from src.core.config import settings
from src.core.database import engine

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting Mage Audit", version="0.1.0")

    # Verify database connection
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("Database connected", url=settings.database_url.split("@")[-1])

    # Verify Redis connection
    redis = aioredis.from_url(settings.redis_url)
    await redis.ping()
    await redis.aclose()
    logger.info("Redis connected")

    yield

    # Shutdown
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Mage Audit",
    description="AI-powered architecture auditor for Magento codebases",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    checks = {}

    # Check database
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # Check Redis
    try:
        redis = aioredis.from_url(settings.redis_url)
        await redis.ping()
        await redis.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    # Check pgvector extension
    try:
        async with engine.begin() as conn:
            result = await conn.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            )
            row = result.fetchone()
            checks["pgvector"] = row[0] if row else "not installed"
    except Exception as e:
        checks["pgvector"] = f"error: {e}"

    all_ok = all(v == "ok" or v.startswith("0.") for v in checks.values())

    return {
        "status": "healthy" if all_ok else "unhealthy",
        "version": "0.1.0",
        "checks": checks,
    }
