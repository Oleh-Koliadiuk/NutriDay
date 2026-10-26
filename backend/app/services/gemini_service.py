import json
import re
import time
from typing import Any

from google import genai
from google.genai import types

from ..core.config import settings


class GeminiService:
    MODEL = "gemini-3.8-flash"
    FALLBACK_MODEL = "gemini-3.1-flash-lite"
    RECIPE_MODEL = "gemini-3.1-flash-lite"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.gemini_api_key
        self.client = (
            genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(timeout=20_000),
            )
            if self.api_key
            else None
        )

    def _generate_content(self, contents: Any) -> Any:
        if not self.client:
            raise RuntimeError("Gemini API client is not configured")

        last_error: Exception | None = None
        for model, attempts in ((self.MODEL, 2), (self.FALLBACK_MODEL, 1)):
            for attempt in range(attempts):
                try:
                    return self.client.models.generate_content(model=model, contents=contents)
                except Exception as exc:
                    if not self._is_temporary_capacity_error(exc):
                        raise
                    last_error = exc
                    if attempt + 1 < attempts:
                        # Retry the primary model once, then use the fallback.
                        time.sleep(0.5)

        if last_error:
            raise last_error
        raise RuntimeError("Gemini models are temporarily unavailable")

    @staticmethod
    def _is_temporary_capacity_error(exc: Exception) -> bool:
        code = getattr(exc, "code", None)
        details = f"{code or ''} {exc}".upper()
        return code in (429, 503) or "429" in details or "503" in details or "UNAVAILABLE" in details or "RESOURCE_EXHAUSTED" in details

    def _parse_json(self, text: str) -> dict[str, Any]:
        if not text:
            return {}
        text = text.strip()
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.DOTALL)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            try:
                cleaned = text[text.find("{"): text.rfind("}") + 1]
                return json.loads(cleaned)
            except Exception:
                return {"summary": text}

    def calculate_profile_targets(
        self,
        age: int | None,
        height: int | None,
        weight: float | None,
    ) -> dict[str, float] | None:
        if not self.client or age is None or height is None or weight is None:
            return None

        prompt = (
            "Розрахуй орієнтовну добову норму калорій і макронутрієнтів для дорослої людини "
            "за віком, зростом та вагою. Використай помірний рівень активності. "
            "Поверни тільки JSON з числовими полями calories, protein, carbs, fat. "
            "Калорії мають бути в ккал, макронутрієнти — у грамах. "
            "Це загальна оцінка, не медична рекомендація. "
            f"Вік: {age}; зріст: {height} см; вага: {weight} кг."
        )
        try:
            response = self._generate_content(prompt)
            payload = self._parse_json(response.text or "")
            targets = {
                "calories": float(payload["calories"]),
                "protein": float(payload["protein"]),
                "carbs": float(payload["carbs"]),
                "fat": float(payload["fat"]),
            }
            limits = {
                "calories": (1200, 6000),
                "protein": (30, 500),
                "carbs": (30, 800),
                "fat": (20, 300),
            }
            if any(not low <= targets[key] <= high for key, (low, high) in limits.items()):
                return None
            return targets
        except Exception:  # pragma: no cover - API fallback
            return None

    def generate_daily_insight(self, day_data: dict[str, Any]) -> str:
        if not self.client:
            remaining = max(0, round(day_data["calorie_target"] - day_data["calories"]))
            if day_data["meals"]:
                return (
                    f"За сьогодні записано {len(day_data['meals'])} прийом(и) їжі. "
                    f"До орієнтовної денної цілі залишилося близько {remaining} ккал. "
                    "Орієнтуйся на самопочуття та збалансовані порції."
                )
            return "Додай першу страву, щоб отримати підказку за підсумком дня."

        meals = "\n".join(
            f"- {meal['name']}: {meal['calories']} ккал; білки {meal['protein']} г, "
            f"вуглеводи {meal['carbs']} г, жири {meal['fat']} г"
            for meal in day_data["meals"]
        ) or "Страви поки не записані."
        prompt = (
            "Дай одну коротку доброзичливу підказку українською за денним харчовим журналом. "
            "Не сором і не діагностуй. Не радь екстремально обмежувати калорії. "
            "Врахуй баланс білків, вуглеводів, жирів і калорій та сформулюй одну практичну ідею. "
            f"Ціль: {day_data['calorie_target']} ккал, Б {day_data['protein_target']} г, "
            f"В {day_data['carbs_target']} г, Ж {day_data['fat_target']} г. "
            f"З'їдено: {day_data['calories']} ккал, Б {day_data['protein']} г, "
            f"В {day_data['carbs']} г, Ж {day_data['fat']} г. Страви:\n{meals}"
        )
        try:
            response = self._generate_content(prompt)
            return (response.text or "").strip() or "Продовжуй записувати страви — так легше бачити загальний баланс."
        except Exception:  # pragma: no cover - API fallback
            return "Продовжуй записувати страви — так легше бачити загальний баланс."

    def analyze_meal_text(self, meal_text: str) -> dict[str, Any]:
        if not self.client:
            return {
                "total_calories": 0,
                "protein": 0,
                "carbs": 0,
                "fat": 0,
                "summary": "Gemini key is missing. Please set GEMINI_API_KEY.",
            }

        prompt = (
            "Проаналізуй текст із продуктами та стравами, що з'їв користувач. "
            "Поверни результат у валідному JSON без пояснень. "
            "Поля: total_calories (число), protein (г), carbs (г), fat (г), summary (коротко). "
            "Підрахунок має бути розумним для української російської англійської мови. "
            f"Текст: {meal_text}"
        )

        try:
            response = self._generate_content(prompt)
            payload = self._parse_json(response.text)
            return {
                "total_calories": float(payload.get("total_calories", 0) or 0),
                "protein": float(payload.get("protein", 0) or 0),
                "carbs": float(payload.get("carbs", 0) or 0),
                "fat": float(payload.get("fat", 0) or 0),
                "summary": payload.get("summary", "Meal analyzed successfully."),
            }
        except Exception as exc:  # pragma: no cover - API-level fallback
            return {
                "total_calories": 0,
                "protein": 0,
                "carbs": 0,
                "fat": 0,
                "summary": f"Gemini request error: {exc}",
            }

    def analyze_food_image(self, file_bytes: bytes, file_name: str, dish_name: str, portion_grams: float) -> dict[str, Any]:
        if not self.client:
            return {
                "estimated_calories": 0,
                "protein": 0,
                "carbs": 0,
                "fat": 0,
                "summary": "Gemini key is missing. Please set GEMINI_API_KEY.",
            }

        mime_type = "image/jpeg"
        if file_name.lower().endswith(".png"):
            mime_type = "image/png"

        prompt = (
            "Проаналізуй фото страви. Визнач приблизну калорійність, білки, вуглеводи, жири для поданої порції. "
            "Поверни результат тільки як JSON: estimated_calories, protein, carbs, fat, summary. "
            f"Назва страви: {dish_name}. Грамовка порції: {portion_grams} грам. "
            "Не пиши зайві текстові пояснення."
        )

        try:
            part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
            response = self._generate_content([prompt, part])
            payload = self._parse_json(response.text)
            return {
                "estimated_calories": float(payload.get("estimated_calories", 0) or 0),
                "protein": float(payload.get("protein", 0) or 0),
                "carbs": float(payload.get("carbs", 0) or 0),
                "fat": float(payload.get("fat", 0) or 0),
                "summary": payload.get("summary", "Image analyzed successfully."),
            }
        except Exception as exc:  # pragma: no cover - API-level fallback
            return {
                "estimated_calories": 0,
                "protein": 0,
                "carbs": 0,
                "fat": 0,
                "summary": f"Gemini image analysis error: {exc}",
            }

    def generate_recipe(
        self,
        title: str,
        target_weight_g: float,
        servings: int,
        dietary_preferences: str,
        language: str,
    ) -> dict[str, Any]:
        if not self.client:
            raise RuntimeError("Gemini key is missing. Please set GEMINI_API_KEY.")

        language_names = {"uk": "українською", "ru": "російською", "en": "англійською"}
        output_language = language_names.get(language, language_names["uk"])
        prompt = (
            "Склади короткий, практичний домашній рецепт. Відповідай тільки JSON, без markdown. "
            "Поля: title, description, total_weight_g, servings, ingredients (name, grams, note), "
            "instructions (4-6 коротких кроків), calories, protein, carbs, fat. "
            "Грамовки мають бути реалістичними, загальна вага — близькою до цільової. "
            "КБЖВ — орієнтовно для всієї готової страви. Не додавай зайвих пояснень. "
            f"Мова: {output_language}. Страва: {title.strip()}. "
            f"Готова вага: {target_weight_g:g} г. Порцій: {servings}. "
            f"Побажання: {dietary_preferences.strip() or 'немає'}"
        )
        primary_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            max_output_tokens=1400,
        )
        fallback_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            max_output_tokens=1400,
        )
        last_error: Exception | None = None
        for model, config in (
            (self.RECIPE_MODEL, primary_config),
            (self.MODEL, fallback_config),
        ):
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config,
                )
                break
            except Exception as exc:
                last_error = exc
        else:
            if last_error:
                raise last_error
            raise RuntimeError("Recipe generation is temporarily unavailable")

        payload = self._parse_json(response.text or "")
        ingredients = payload.get("ingredients")
        instructions = payload.get("instructions")
        if not isinstance(ingredients, list) or not ingredients:
            raise ValueError("Recipe response does not include ingredients")
        if not isinstance(instructions, list) or not instructions:
            raise ValueError("Recipe response does not include preparation steps")

        parsed_ingredients = []
        for item in ingredients[:50]:
            if not isinstance(item, dict) or not str(item.get("name", "")).strip():
                continue
            parsed_ingredients.append({
                "name": str(item["name"]).strip()[:120],
                "grams": max(0, float(item.get("grams", 0) or 0)),
                "note": str(item.get("note", "") or "")[:200],
            })
        parsed_steps = [str(step).strip()[:1000] for step in instructions[:40] if str(step).strip()]
        if not parsed_ingredients or not parsed_steps:
            raise ValueError("Recipe response is incomplete")

        return {
            "title": str(payload.get("title") or title).strip()[:160],
            "description": str(payload.get("description") or "").strip()[:2000],
            "total_weight_g": max(1, float(payload.get("total_weight_g") or target_weight_g)),
            "servings": max(1, int(payload.get("servings") or servings)),
            "ingredients": parsed_ingredients,
            "instructions": parsed_steps,
            "calories": max(0, float(payload.get("calories", 0) or 0)),
            "protein": max(0, float(payload.get("protein", 0) or 0)),
            "carbs": max(0, float(payload.get("carbs", 0) or 0)),
            "fat": max(0, float(payload.get("fat", 0) or 0)),
        }
