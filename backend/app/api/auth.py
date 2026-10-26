from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.dependencies import get_current_user
from ..core.security import generate_token, hash_password, verify_password
from ..database.session import get_db
from ..models import DailyLog, User
from ..schemas import TokenOut, UserCreate, UserLogin, UserOut, UserSkip, UserUpdate
from ..services.calorie_targets import calculate_daily_targets
from ..services.gemini_service import GeminiService

router = APIRouter(prefix="/auth", tags=["auth"])


def _serialize_user(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        name=user.name,
        age=user.age,
        height=user.height,
        weight=user.weight,
        daily_calories=user.daily_calories,
        protein_goal=user.protein_goal,
        carbs_goal=user.carbs_goal,
        fat_goal=user.fat_goal,
    )


@router.post("/register", response_model=TokenOut)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User with this name already exists")

    targets = calculate_daily_targets(payload.age, payload.height, payload.weight)
    token = generate_token()
    user = User(
        name=payload.name,
        password_hash=hash_password(payload.password),
        age=payload.age,
        height=payload.height,
        weight=payload.weight,
        daily_calories=targets["calories"],
        protein_goal=targets["protein"],
        carbs_goal=targets["carbs"],
        fat_goal=targets["fat"],
        api_token=token,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenOut(token=token, user=_serialize_user(user))


@router.post("/login", response_model=TokenOut)
def login_user(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.name == payload.name).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = generate_token()
    user.api_token = token
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenOut(token=token, user=_serialize_user(user))


@router.post("/skip", response_model=TokenOut)
def skip_signup(payload: UserSkip, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User with this name already exists")

    targets = calculate_daily_targets(None, None, None)
    token = generate_token()
    user = User(
        name=payload.name,
        password_hash=hash_password(payload.password),
        age=None,
        height=None,
        weight=None,
        daily_calories=targets["calories"],
        protein_goal=targets["protein"],
        carbs_goal=targets["carbs"],
        fat_goal=targets["fat"],
        api_token=token,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenOut(token=token, user=_serialize_user(user))


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return _serialize_user(current_user)


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates:
        existing = db.query(User).filter(
            User.name == updates["name"],
            User.id != current_user.id,
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User with this name already exists")

    for field in ("name", "age", "height", "weight"):
        if field in updates:
            setattr(current_user, field, updates[field])

    if any(field in updates for field in ("age", "height", "weight")):
        targets = GeminiService().calculate_profile_targets(
            current_user.age,
            current_user.height,
            current_user.weight,
        ) or calculate_daily_targets(current_user.age, current_user.height, current_user.weight)
        current_user.daily_calories = targets["calories"]
        current_user.protein_goal = targets["protein"]
        current_user.carbs_goal = targets["carbs"]
        current_user.fat_goal = targets["fat"]

        today_log = db.query(DailyLog).filter(
            DailyLog.user_id == current_user.id,
            DailyLog.day == date.today(),
        ).first()
        if today_log:
            today_log.calorie_target = current_user.daily_calories
            today_log.protein_target = current_user.protein_goal
            today_log.carbs_target = current_user.carbs_goal
            today_log.fat_target = current_user.fat_goal

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return _serialize_user(current_user)
