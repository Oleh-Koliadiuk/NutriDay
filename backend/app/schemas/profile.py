from pydantic import BaseModel, Field

from .auth import EMAIL_PATTERN


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    email: str | None = Field(default=None, min_length=6, max_length=254, pattern=EMAIL_PATTERN)
    age: int | None = Field(default=None, ge=10, le=120)
    height: int | None = Field(default=None, ge=100, le=260)
    weight: float | None = Field(default=None, ge=30, le=300)
