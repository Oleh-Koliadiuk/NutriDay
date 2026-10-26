def calculate_daily_targets(
    age: int | None,
    height: int | None,
    weight: float | None,
) -> dict[str, int]:
    if age is None or height is None or weight is None:
        return {"calories": 2100, "protein": 130, "carbs": 240, "fat": 70}

    bmr = 10 * weight + 6.25 * height - 5 * age + 5
    calories = round(bmr * 1.375)
    return {
        "calories": max(1600, calories),
        "protein": max(90, round((calories * 0.30) / 4)),
        "carbs": max(180, round((calories * 0.45) / 4)),
        "fat": max(50, round((calories * 0.25) / 9)),
    }
