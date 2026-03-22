from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    project_name: str = Field(default="IT News Platform", alias="PROJECT_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    postgres_db: str = Field(default="itnews", alias="POSTGRES_DB")
    postgres_user: str = Field(default="itnews", alias="POSTGRES_USER")
    postgres_password: str = Field(default="itnews", alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(default="postgres", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")

    neo4j_uri: str = Field(default="bolt://neo4j:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="please-change-me", alias="NEO4J_PASSWORD")

    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")

    qdrant_host: str = Field(default="qdrant", alias="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, alias="QDRANT_PORT")
    qdrant_collection: str = Field(default="articles", alias="QDRANT_COLLECTION")

    enable_scheduler: bool = Field(default=True, alias="ENABLE_SCHEDULER")
    ingestion_interval_minutes: int = Field(default=30, alias="INGESTION_INTERVAL_MINUTES")
    enable_news_api: bool = Field(default=False, alias="ENABLE_NEWS_API")
    news_api_url: str = Field(default="https://newsapi.org/v2/everything", alias="NEWS_API_URL")
    news_api_key: str = Field(default="", alias="NEWS_API_KEY")
    news_api_query: str = Field(default="technology OR cybersecurity OR software", alias="NEWS_API_QUERY")

    default_language: str = Field(default="en", alias="DEFAULT_LANGUAGE")
    supported_languages: str = Field(default="ru,en", alias="SUPPORTED_LANGUAGES")
    allowed_rss_sources: str = Field(
        default="https://techcrunch.com/feed/,https://www.wired.com/feed/rss,https://feeds.arstechnica.com/arstechnica/index",
        alias="ALLOWED_RSS_SOURCES",
    )

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def rss_sources(self) -> list[str]:
        return [item.strip() for item in self.allowed_rss_sources.split(",") if item.strip()]

    @property
    def languages(self) -> list[str]:
        return [item.strip() for item in self.supported_languages.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
