import hashlib
import hmac
import logging
import secrets
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.dependencies import get_current_user
from ..core.security import generate_token, hash_password, verify_password
from ..database.session import get_db
from ..models import DailyLog, PasswordResetCode, User
from ..schemas import ForgotPasswordRequest, ResetPasswordRequest, TokenOut, UserCreate, UserLogin, UserOut, UserSkip, UserUpdate
from ..services.calorie_targets import calculate_daily_targets
from ..services.email_service import EmailService

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("uvicorn.error")
RESET_CODE_TTL = timedelta(minutes=10)
RESET_RESEND_DELAY = timedelta(seconds=60)
RESET_CODE_MAX_ATTEMPTS = 5


def _utc_now() -> datetime:
    # SQLite stores DateTime values without timezone metadata; keep DB timestamps in naive UTC.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _serialize_user(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        age=user.age,
        height=user.height,
        weight=user.weight,
        goal=user.goal,
        biological_sex=user.biological_sex,
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
    email = payload.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered")

    targets = calculate_daily_targets(
        payload.age, payload.height, payload.weight, payload.biological_sex, payload.goal
    )
    token = generate_token()
    user = User(
        name=payload.name,
        email=email,
        password_hash=hash_password(payload.password),
        age=payload.age,
        height=payload.height,
        weight=payload.weight,
        goal=payload.goal,
        biological_sex=payload.biological_sex,
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
    identifier = payload.name.strip()
    user = db.query(User).filter(User.name == identifier).first()
    if user is None and "@" in identifier:
        user = db.query(User).filter(User.email == identifier.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = generate_token()
    user.api_token = token
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenOut(token=token, user=_serialize_user(user))


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    logger.info("Password reset request received")
    if not EmailService.is_configured():
        logger.error("Password reset email skipped: SMTP is not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="email_service_not_configured",
        )

    now = _utc_now()
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        logger.info("Password reset email skipped: no matching account")
    else:
        recent_code = (
            db.query(PasswordResetCode)
            .filter(
                PasswordResetCode.user_id == user.id,
                PasswordResetCode.created_at > now - RESET_RESEND_DELAY,
            )
            .order_by(PasswordResetCode.created_at.desc())
            .first()
        )
        hourly_code_count = (
            db.query(PasswordResetCode)
            .filter(
                PasswordResetCode.user_id == user.id,
                PasswordResetCode.created_at > now - timedelta(hours=1),
            )
            .count()
        )
        if recent_code is not None:
            logger.info("Password reset email skipped: resend cooldown is active")
        elif hourly_code_count >= 5:
            logger.info("Password reset email skipped: hourly limit reached")
        else:
            code = f"{secrets.randbelow(1_000_000):06d}"
            reset_code = PasswordResetCode(
                user_id=user.id,
                code_hash=hashlib.sha256(code.encode("utf-8")).hexdigest(),
                created_at=now,
                expires_at=now + RESET_CODE_TTL,
            )
            db.query(PasswordResetCode).filter(
                PasswordResetCode.user_id == user.id,
                PasswordResetCode.used_at.is_(None),
            ).update({PasswordResetCode.used_at: now}, synchronize_session=False)
            db.add(reset_code)
            db.commit()
            try:
                EmailService.send_password_reset_code(email, code)
            except Exception:
                logger.exception("Could not deliver a NutriDay password reset email")
                reset_code.used_at = now
                db.add(reset_code)
                db.commit()
            else:
                logger.info("Password reset email accepted by SMTP relay")

    # Avoid revealing whether an email address belongs to an account.
    return {"message": "If the email is registered, a reset code has been sent."}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    now = _utc_now()
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    reset_code = None
    if user:
        reset_code = (
            db.query(PasswordResetCode)
            .filter(
                PasswordResetCode.user_id == user.id,
                PasswordResetCode.used_at.is_(None),
            )
            .order_by(PasswordResetCode.created_at.desc())
            .first()
        )

    if not user or not reset_code or reset_code.expires_at <= now or reset_code.attempts >= RESET_CODE_MAX_ATTEMPTS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="reset_code_invalid")

    submitted_hash = hashlib.sha256(payload.code.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(submitted_hash, reset_code.code_hash):
        reset_code.attempts += 1
        if reset_code.attempts >= RESET_CODE_MAX_ATTEMPTS:
            reset_code.used_at = now
        db.add(reset_code)
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="reset_code_invalid")

    changed_at = user.password_changed_at
    if changed_at is not None and now < changed_at + timedelta(days=7):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="password_change_cooldown")
    if verify_password(payload.new_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="new_password_same")

    user.password_hash = hash_password(payload.new_password)
    user.password_changed_at = now
    user.api_token = None
    reset_code.used_at = now
    db.add_all([user, reset_code])
    db.commit()
    return {"message": "password_reset_success"}


@router.post("/skip", response_model=TokenOut)
def skip_signup(payload: UserSkip, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User with this name already exists")

    targets = calculate_daily_targets(None, None, None)
    token = generate_token()
    user = User(
        name=payload.name,
        email=None,
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

    for field in ("name", "age", "height", "weight", "goal", "biological_sex"):
        if field in updates:
            setattr(current_user, field, updates[field])

    if "email" in updates:
        email = updates["email"].strip().lower() if updates["email"] else None
        existing_email = db.query(User).filter(
            User.email == email,
            User.id != current_user.id,
        ).first() if email else None
        if existing_email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered")
        current_user.email = email

    if any(field in updates for field in ("age", "height", "weight", "goal", "biological_sex")):
        targets = calculate_daily_targets(
            current_user.age,
            current_user.height,
            current_user.weight,
            current_user.biological_sex,
            current_user.goal,
        )
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
            today_log.insight = None

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return _serialize_user(current_user)
