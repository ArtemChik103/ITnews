import asyncio

from sqlalchemy import text

from app.db.session import engine


async def check_postgres() -> bool:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return True


async def run_healthcheck() -> dict:
    try:
        await check_postgres()
        return {
            "status": "ok",
            "components": {
                "postgres": "ok",
            },
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "degraded",
            "components": {
                "postgres": f"error: {exc}",
            },
        }
