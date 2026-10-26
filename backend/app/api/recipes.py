from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.dependencies import get_current_user
from ..database.session import get_db
from ..models import SavedRecipe, User
from ..schemas.recipe import RecipeGenerateRequest, RecipeOut, RecipeWrite
from ..services.gemini_service import GeminiService

router = APIRouter(prefix="/recipes", tags=["recipes"])


def _recipe_values(payload: RecipeWrite) -> dict:
    values = payload.model_dump()
    values["ingredients"] = [item.model_dump() for item in payload.ingredients]
    return values


def _owned_recipe(db: Session, user: User, recipe_id: int) -> SavedRecipe | None:
    return db.query(SavedRecipe).filter(
        SavedRecipe.id == recipe_id,
        SavedRecipe.user_id == user.id,
    ).first()


@router.post("/generate")
def generate_recipe(
    payload: RecipeGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        return GeminiService().generate_recipe(
            title=payload.title,
            target_weight_g=payload.target_weight_g,
            servings=payload.servings,
            dietary_preferences=payload.dietary_preferences,
            language=payload.language,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Recipe generation is temporarily unavailable: {exc}",
        ) from exc


@router.get("", response_model=list[RecipeOut])
def list_recipes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(SavedRecipe).filter(
        SavedRecipe.user_id == current_user.id,
    ).order_by(SavedRecipe.updated_at.desc(), SavedRecipe.id.desc()).all()


@router.post("", response_model=RecipeOut, status_code=status.HTTP_201_CREATED)
def create_recipe(
    payload: RecipeWrite,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recipe = SavedRecipe(user_id=current_user.id, **_recipe_values(payload))
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


@router.patch("/{recipe_id}", response_model=RecipeOut)
def update_recipe(
    recipe_id: int,
    payload: RecipeWrite,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recipe = _owned_recipe(db, current_user, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    for field, value in _recipe_values(payload).items():
        setattr(recipe, field, value)
    db.commit()
    db.refresh(recipe)
    return recipe


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(
    recipe_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recipe = _owned_recipe(db, current_user, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found")
    db.delete(recipe)
    db.commit()
