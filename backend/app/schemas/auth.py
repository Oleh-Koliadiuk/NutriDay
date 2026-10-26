from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    password: str = Field(..., min_length=6)
    age: int | None = None
    height: int | None = None
    weight: float | None = None


class UserLogin(BaseModel):
    name: str
    password: str


class UserSkip(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    password: str = Field(..., min_length=6)


class UserOut(BaseModel):
    id: int
    name: str
    age: int | None = None
    height: int | None = None
    weight: float | None = None
    daily_calories: float
    protein_goal: float
    carbs_goal: float
    fat_goal: float

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    token: str
    user: UserOut
