from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models import DailyLog, MealEntry, User
from ..schemas.nutrition import DaySummaryOut, HistoryDayOut


def get_or_create_daily_log(db: Session, user: User, day: date) -> DailyLog:
    log = db.query(DailyLog).filter(DailyLog.user_id == user.id, DailyLog.day == day).first()
    if log:
        return log

    log = DailyLog(
        user_id=user.id,
        day=day,
        calorie_target=user.daily_calories,
        protein_target=user.protein_goal,
        carbs_target=user.carbs_goal,
        fat_target=user.fat_goal,
    )
    db.add(log)
    db.flush()
    return log


def get_day_summary(db: Session, user: User, day: date) -> DaySummaryOut:
    log = db.query(DailyLog).filter(DailyLog.user_id == user.id, DailyLog.day == day).first()
    meals = db.query(MealEntry).join(DailyLog).filter(
        DailyLog.user_id == user.id,
        DailyLog.day == day,
    ).order_by(MealEntry.created_at.asc(), MealEntry.id.asc()).all()

    return DaySummaryOut(
        day=day,
        calorie_target=log.calorie_target if log else user.daily_calories,
        protein_target=log.protein_target if log else user.protein_goal,
        carbs_target=log.carbs_target if log else user.carbs_goal,
        fat_target=log.fat_target if log else user.fat_goal,
        calories=sum(meal.calories for meal in meals),
        protein=sum(meal.protein for meal in meals),
        carbs=sum(meal.carbs for meal in meals),
        fat=sum(meal.fat for meal in meals),
        insight=log.insight if log else None,
        meals=meals,
    )


def get_history(db: Session, user: User, limit: int = 60) -> list[HistoryDayOut]:
    logs = db.query(DailyLog).filter(DailyLog.user_id == user.id).order_by(DailyLog.day.desc()).limit(limit).all()
    history = []
    for log in logs:
        calories, meal_count = db.query(
            func.coalesce(func.sum(MealEntry.calories), 0),
            func.count(MealEntry.id),
        ).filter(MealEntry.daily_log_id == log.id).one()
        history.append(HistoryDayOut(
            day=log.day,
            calorie_target=log.calorie_target,
            calories=float(calories),
            meal_count=meal_count,
        ))
    return history


def get_owned_meal(db: Session, user: User, meal_id: int) -> MealEntry | None:
    return db.query(MealEntry).join(DailyLog).filter(
        MealEntry.id == meal_id,
        DailyLog.user_id == user.id,
    ).first()
