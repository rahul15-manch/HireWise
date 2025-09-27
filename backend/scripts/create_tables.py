# backend/scripts/create_tables.py
import asyncio
from backend.app.core.database import engine, Base

async def create_tables():
    async with engine.begin() as conn:
        # Use `run_sync` with a callable to create all tables
        await conn.run_sync(Base.metadata.create_all)

    # Optional: Close the engine after creation
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_tables())
