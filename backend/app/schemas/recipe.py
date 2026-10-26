from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RecipeGenerateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=120)
    target_weight_g: float = Field(..., gt=0, le=5000)
    servings: int = Field(default=2, ge=1, le=20)
    dietary_preferences: str = Field(default="", max_length=500)
    language: Literal["uk", "ru", "en"] = "uk"


class RecipeIngredient(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    grams: float = Field(..., ge=0, le=10000)
    note: str = Field(default="", max_length=200)


class RecipeWrite(BaseModel):
    title: str = Field(..., min_length=1, max_length=160)
    description: str = Field(default="", max_length=2000)
    total_weight_g: float = Field(..., gt=0, le=10000)
    servings: int = Field(..., ge=1, le=50)
    ingredients: list[RecipeIngredient] = Field(..., min_length=1, max_length=50)
    instructions: list[str] = Field(..., min_length=1, max_length=40)
    calories: float = Field(..., ge=0, le=50000)
    protein: float = Field(..., ge=0, le=5000)
    carbs: float = Field(..., ge=0, le=10000)
    fat: float = Field(..., ge=0, le=5000)


class RecipeOut(RecipeWrite):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
