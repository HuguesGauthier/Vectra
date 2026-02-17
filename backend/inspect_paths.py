import asyncio
from app.core.database import SessionLocal
from app.models.connector import Connector
from sqlalchemy import select


async def run():
    async with SessionLocal() as db:
        res = await db.execute(select(Connector))
        for c in res.scalars():
            print(f"DEBUG_ID: {c.id}")
            print(f"DEBUG_PATH: {c.configuration.get('path')}")


if __name__ == "__main__":
    asyncio.run(run())
