import asyncio
from app.db.database import AsyncSessionLocal
from sqlalchemy import text


async def clear():
    async with AsyncSessionLocal() as s:
        await s.execute(text("DELETE FROM style_profiles"))
        await s.commit()


if __name__ == "__main__":
    asyncio.run(clear())
