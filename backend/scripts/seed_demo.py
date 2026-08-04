import asyncio
import os
import sys

# Ensure the app module can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import SessionLocal, engine
from app.models.user import User
from app.models.style import StyleProfile
from app.core.security import get_password_hash


async def seed_demo():
    async with SessionLocal() as db:
        print("Creating demo user...")
        demo_user = User(
            email="demo@personanotes.ai",
            name="Demo User",
            hashed_password=get_password_hash("demo123"),
        )
        db.add(demo_user)
        await db.commit()
        await db.refresh(demo_user)

        print("Creating style profile...")
        profile = StyleProfile(
            user_id=demo_user.id,
            version=1,
            profile_json={
                "tone": "Academic",
                "format_preference": "Bullet points",
                "avg_sentence_length": 15,
                "example_density": "High",
            },
        )
        db.add(profile)
        await db.commit()

        print(
            "Demo database seeded successfully. Login with demo@personanotes.ai / demo123"
        )


if __name__ == "__main__":
    asyncio.run(seed_demo())
