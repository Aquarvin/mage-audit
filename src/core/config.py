from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    google_api_key: str = ""
    llm_provider: str = "gemini"
    llm_model: str = "gemini-2.0-flash"

    # Embeddings
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    # Database
    database_url: str = (
        "postgresql+asyncpg://mageaudit:dev_password@localhost:5433/mage_audit"
    )

    # Redis
    redis_url: str = "redis://localhost:6380/0"

    # App
    log_level: str = "INFO"

    model_config = {"env_file": ".env"}


settings = Settings()
