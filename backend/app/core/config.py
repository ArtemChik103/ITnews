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
    qdrant_collection: str = Field(default="news_articles", alias="QDRANT_COLLECTION")

    enable_scheduler: bool = Field(default=True, alias="ENABLE_SCHEDULER")
    ingestion_interval_minutes: int = Field(default=30, alias="INGESTION_INTERVAL_MINUTES")
    embedding_index_interval_minutes: int = Field(default=5, alias="EMBEDDING_INDEX_INTERVAL_MINUTES")
    clustering_interval_minutes: int = Field(default=30, alias="CLUSTERING_INTERVAL_MINUTES")
    enable_news_api: bool = Field(default=False, alias="ENABLE_NEWS_API")
    news_api_url: str = Field(default="https://newsapi.org/v2/everything", alias="NEWS_API_URL")
    news_api_key: str = Field(default="", alias="NEWS_API_KEY")
    news_api_query: str = Field(default="technology OR cybersecurity OR software", alias="NEWS_API_QUERY")
    embedding_model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        alias="EMBEDDING_MODEL",
    )
    embedding_dimension: int = Field(default=384, alias="EMBEDDING_DIMENSION")
    embedding_max_chars: int = Field(default=4000, alias="EMBEDDING_MAX_CHARS")
    embedding_max_retries: int = Field(default=3, alias="EMBEDDING_MAX_RETRIES")
    clustering_hdbscan_threshold: int = Field(default=50, alias="CLUSTERING_HDBSCAN_THRESHOLD")
    clustering_min_cluster_size: int = Field(default=5, alias="CLUSTERING_MIN_CLUSTER_SIZE")
    llm_provider: str = Field(default="groq", alias="LLM_PROVIDER")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model_primary: str = Field(default="openai/gpt-oss-120b", alias="GROQ_MODEL_PRIMARY")
    groq_model_fallback: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL_FALLBACK")
    groq_model_fast: str = Field(default="llama-3.1-8b-instant", alias="GROQ_MODEL_FAST")
    groq_api_url: str = Field(
        default="https://api.groq.com/openai/v1/chat/completions",
        alias="GROQ_API_URL",
    )
    groq_timeout_seconds: int = Field(default=45, alias="GROQ_TIMEOUT_SECONDS")
    rag_top_k: int = Field(default=5, alias="RAG_TOP_K")
    graph_max_entities: int = Field(default=15, alias="GRAPH_MAX_ENTITIES")
    graph_max_relations: int = Field(default=20, alias="GRAPH_MAX_RELATIONS")
    rag_max_article_snippet_chars: int = Field(default=700, alias="RAG_MAX_ARTICLE_SNIPPET_CHARS")
    rag_context_token_budget: int = Field(default=8000, alias="RAG_CONTEXT_TOKEN_BUDGET")

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
