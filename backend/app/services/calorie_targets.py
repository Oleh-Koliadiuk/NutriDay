def calculate_daily_targets(
    age: int | None,
    height: int | None,
    weight: float | None,
    biological_sex: str | None = None,
    goal: str = "maintain",
) -> dict[str, int]:
    if age is None or height is None or weight is None:
        return {"calories": 2100, "protein": 130, "carbs": 240, "fat": 70}

    # Teen calorie needs depend on growth and activity in ways this profile does
    # not capture. Keep the existing neutral baseline and avoid weight-change targets.
    if age < 18:
        return {"calories": 2100, "protein": 130, "carbs": 240, "fat": 70}

    # Mifflin–St Jeor estimate with light activity; when sex is not set,
    # use the midpoint between the two equation constants.
    sex_adjustment = {"male": 5, "female": -161}.get(biological_sex, -78)
    maintenance = round((10 * weight + 6.25 * height - 5 * age + sex_adjustment) * 1.375)
    if goal == "lose_weight":
        calories = max(1200, round(maintenance * 0.85))
    elif goal == "gain_mass":
        calories = maintenance + 200
    else:
        calories = maintenance

    protein_factor = {
        "lose_weight": 1.6,
        "gain_mass": 1.8,
        "sports": 1.6,
        "maintain": 1.4,
    }.get(goal, 1.4)
    protein = round(weight * protein_factor)
    fat = round((calories * 0.27) / 9)
    carbs = round(max(0, (calories - protein * 4 - fat * 9) / 4))
    return {
        "calories": max(1200, calories),
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
    }
