
from sqlalchemy import String, Integer, DateTime, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from database.base import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[str] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(100))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    risk_level: Mapped[str] = mapped_column(String(20), default="medium")
    horizon: Mapped[str] = mapped_column(String(20), default="long")
