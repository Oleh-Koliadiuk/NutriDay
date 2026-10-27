from pydantic import BaseModel, Field

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    email: str = Field(..., min_length=6, max_length=254, pattern=EMAIL_PATTERN)
    password: str = Field(..., min_length=6)
    age: int | None = None
    height: int | None = None
    weight: float | None = None


class UserLogin(BaseModel):
    name: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., min_length=6, max_length=254, pattern=EMAIL_PATTERN)


class ResetPasswordRequest(BaseModel):
    email: str = Field(..., min_length=6, max_length=254, pattern=EMAIL_PATTERN)
    code: str = Field(..., pattern=r"^\d{6}$")
    new_password: str = Field(..., min_length=6, max_length=128)


class UserSkip(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    password: str = Field(..., min_length=6)


class UserOut(BaseModel):
    id: int
    name: str
    email: str | None = None
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
