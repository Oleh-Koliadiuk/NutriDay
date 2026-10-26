from datetime import date as date_type, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base


class DailyLog(Base):
    __tablename__ = "daily_logs"
    __table_args__ = (UniqueConstraint("user_id", "day", name="uq_daily_log_user_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    day: Mapped[date_type] = mapped_column(Date, index=True, nullable=False)
    calorie_target: Mapped[float] = mapped_column(Float, nullable=False)
    protein_target: Mapped[float] = mapped_column(Float, nullable=False)
    carbs_target: Mapped[float] = mapped_column(Float, nullable=False)
    fat_target: Mapped[float] = mapped_column(Float, nullable=False)
    insight: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
