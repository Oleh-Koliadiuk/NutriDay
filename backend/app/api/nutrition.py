from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from ..core.dependencies import get_current_user
from ..database.session import get_db
from ..models import DailyLog, MealEntry, User
from ..schemas import DaySummaryOut, HistoryDayOut, MealAnalysisRequest, MealEntryUpdate
from ..schemas.nutrition import MealEntryOut
from ..services.gemini_service import GeminiService
from ..services.nutrition_service import get_day_summary, get_history, get_or_create_daily_log, get_owned_meal

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


def _day_or_today(day: date | None) -> date:
    return day or date.today()


def _save_meal(
    db: Session,
    user: User,
    day: date,
    name: str,
    description: str,
    source: str,
    calories: float,
    protein: float,
    carbs: float,
    fat: float,
    summary: str,
) -> MealEntry:
    log = get_or_create_daily_log(db, user, day)
    log.insight = None
    meal = MealEntry(
        daily_log_id=log.id,
        name=name[:160],
        description=description,
        source=source,
        calories=max(0, calories),
        protein=max(0, protein),
        carbs=max(0, carbs),
        fat=max(0, fat),
        summary=summary,
    )
    db.add(meal)
    db.commit()
    db.refresh(meal)
    return meal


@router.get("/profile")
def get_daily_summary(current_user: User = Depends(get_current_user)):
    return {
        "daily_calories": current_user.daily_calories,
        "protein_goal": current_user.protein_goal,
        "carbs_goal": current_user.carbs_goal,
        "fat_goal": current_user.fat_goal,
    }


@router.get("/day", response_model=DaySummaryOut)
def get_day(
    day: date | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_day_summary(db, current_user, _day_or_today(day))


@router.get("/history", response_model=list[HistoryDayOut])
def list_history(
    limit: int = Query(default=60, ge=1, le=180),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_history(db, current_user, limit)


@router.post("/analyze-text")
def analyze_text(
    payload: MealAnalysisRequest,
    day: date | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = GeminiService().analyze_meal_text(payload.meal_text)
    calories = float(analysis.get("total_calories", 0) or 0)
    protein = float(analysis.get("protein", 0) or 0)
    carbs = float(analysis.get("carbs", 0) or 0)
    fat = float(analysis.get("fat", 0) or 0)
    summary = str(analysis.get("summary", ""))
    entry = _save_meal(
        db, current_user, _day_or_today(day), payload.meal_text.strip()[:160],
        payload.meal_text.strip(), "text", calories, protein, carbs, fat, summary,
    )
    return {
        "total_calories": calories,
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
        "summary": summary,
        "entry": MealEntryOut.model_validate(entry),
    }


@router.post("/analyze-image")
async def analyze_image(
    file: UploadFile = File(...),
    dish_name: str = Form(...),
    portion_grams: float = Form(..., gt=0),
    day: date | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image file is empty")

    analysis = GeminiService().analyze_food_image(file_bytes, file.filename or "image.jpg", dish_name, portion_grams)
    calories = float(analysis.get("estimated_calories", 0) or 0)
    protein = float(analysis.get("protein", 0) or 0)
    carbs = float(analysis.get("carbs", 0) or 0)
    fat = float(analysis.get("fat", 0) or 0)
    summary = str(analysis.get("summary", ""))
    entry = _save_meal(
        db, current_user, _day_or_today(day), dish_name.strip(),
        f"{dish_name.strip()}, {portion_grams:g} g · {file.filename or 'image'}", "image",
        calories, protein, carbs, fat, summary,
    )
    return {
        "estimated_calories": calories,
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
        "summary": summary,
        "entry": MealEntryOut.model_validate(entry),
    }


@router.patch("/meals/{meal_id}", response_model=MealEntryOut)
def update_meal(
    meal_id: int,
    payload: MealEntryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    meal = get_owned_meal(db, current_user, meal_id)
    if meal is None:
        raise HTTPException(status_code=404, detail="Meal not found")
    for field, value in payload.model_dump().items():
        setattr(meal, field, value)
    log = db.query(DailyLog).filter(DailyLog.id == meal.daily_log_id).first()
    if log:
        log.insight = None
    db.commit()
    db.refresh(meal)
    return meal


@router.delete("/meals/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meal(
    meal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    meal = get_owned_meal(db, current_user, meal_id)
    if meal is None:
        raise HTTPException(status_code=404, detail="Meal not found")
    log = db.query(DailyLog).filter(DailyLog.id == meal.daily_log_id).first()
    if log:
        log.insight = None
    db.delete(meal)
    db.commit()


@router.post("/insight")
def create_daily_insight(
    day: date | None = Query(default=None),
    language: str = Query(default="uk", pattern="^(uk|ru|en)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    selected_day = _day_or_today(day)
    log = get_or_create_daily_log(db, current_user, selected_day)
    summary = get_day_summary(db, current_user, selected_day)
    insight_data = summary.model_dump()
    insight_data["language"] = language
    insight_data["profile"] = {
        "age": current_user.age,
        "height": current_user.height,
        "weight": current_user.weight,
        "biological_sex": current_user.biological_sex,
        "goal": current_user.goal,
    }
    insight = GeminiService().generate_daily_insight(insight_data)
    log.insight = insight
    db.commit()
    return {"insight": insight}
