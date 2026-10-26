from datetime import date, datetime

from pydantic import BaseModel, Field


class MealAnalysisRequest(BaseModel):
    meal_text: str = Field(..., min_length=3)

class MealEntryUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    description: str = Field(default="", max_length=2000)
    calories: float = Field(..., ge=0, le=20000)
    protein: float = Field(..., ge=0, le=2000)
    carbs: float = Field(..., ge=0, le=2000)
    fat: float = Field(..., ge=0, le=2000)


class MealEntryOut(BaseModel):
    id: int
    name: str
    description: str
    source: str
    calories: float
    protein: float
    carbs: float
    fat: float
    summary: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DaySummaryOut(BaseModel):
    day: date
    calorie_target: float
    protein_target: float
    carbs_target: float
    fat_target: float
    calories: float
    protein: float
    carbs: float
    fat: float
    insight: str | None = None
    meals: list[MealEntryOut]


class HistoryDayOut(BaseModel):
    day: date
    calorie_target: float
    calories: float
    meal_count: int
