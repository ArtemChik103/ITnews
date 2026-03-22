import asyncio

from neo4j import AsyncGraphDatabase
from qdrant_client import QdrantClient
from redis.asyncio import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine


async def check_postgres() -> bool:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return True


async def check_neo4j() -> bool:
    settings = get_settings()
    driver = AsyncGraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
    try:
        await driver.verify_connectivity()
        return True
    finally:
        await driver.close()


async def check_redis() -> bool:
    settings = get_settings()
    client = Redis.from_url(settings.redis_url)
    try:
        await client.ping()
        return True
    finally:
        await client.aclose()


async def check_qdrant() -> bool:
    settings = get_settings()
    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    try:
        client.get_collections()
        return True
    finally:
        client.close()


async def run_healthcheck() -> dict:
    checks = await asyncio.gather(
        check_postgres(),
        check_neo4j(),
        check_redis(),
        check_qdrant(),
        return_exceptions=True,
    )
    names = ["postgres", "neo4j", "redis", "qdrant"]
    components = {
        name: ("ok" if result is True else f"error: {result}")
        for name, result in zip(names, checks, strict=True)
    }
    return {
        "status": "ok" if all(value == "ok" for value in components.values()) else "degraded",
        "components": components,
    }
