from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base


class SavedRecipe(Base):
    __tablename__ = "saved_recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    total_weight_g: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    servings: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    ingredients: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    instructions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    calories: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    protein: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    carbs: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    fat: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
