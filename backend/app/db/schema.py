from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def ensure_article_schema(engine: AsyncEngine) -> None:
    statements = [
        "ALTER TABLE articles ADD COLUMN IF NOT EXISTS embedding_status VARCHAR(16) NOT NULL DEFAULT 'pending'",
        "ALTER TABLE articles ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(255)",
        "ALTER TABLE articles ADD COLUMN IF NOT EXISTS embedded_at TIMESTAMPTZ",
        "ALTER TABLE articles ADD COLUMN IF NOT EXISTS cluster_id INTEGER",
        "ALTER TABLE articles ADD COLUMN IF NOT EXISTS clustered_at TIMESTAMPTZ",
        "ALTER TABLE articles ADD COLUMN IF NOT EXISTS embedding_error TEXT",
        "ALTER TABLE articles ADD COLUMN IF NOT EXISTS embedding_attempts INTEGER NOT NULL DEFAULT 0",
        "UPDATE articles SET embedding_status = 'pending' WHERE embedding_status IS NULL",
        "UPDATE articles SET embedding_attempts = 0 WHERE embedding_attempts IS NULL",
    ]
    async with engine.begin() as connection:
        for statement in statements:
            await connection.execute(text(statement))
