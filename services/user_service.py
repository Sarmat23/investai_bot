
from database.db import SessionLocal
from database.models import User
from sqlalchemy import select

class UserService:

    @staticmethod
    async def get_user(telegram_id: int):
        async with SessionLocal() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def create_user(telegram_id: int, name: str, username: str | None):
        async with SessionLocal() as session:
            user = User(
                telegram_id=telegram_id,
                name=name,
                username=username
            )
            session.add(user)
            await session.commit()
            return user
