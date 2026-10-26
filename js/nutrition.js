import { analyzeMealImage, analyzeMealText } from "./api.js";
import { t } from "./i18n.js";

function showMacros(result, calorieKey, successMessage) {
  return [
    `${t(calorieKey === "total_calories" ? "caloriesTotal" : "caloriesEstimated")}: ${Math.round(result[calorieKey] || 0)} kcal`,
    `${t("proteinLabel")}: ${Math.round(result.protein || 0)} g`,
    `${t("carbsLabel")}: ${Math.round(result.carbs || 0)} g`,
    `${t("fatLabel")}: ${Math.round(result.fat || 0)} g`,
    "",
    result.summary || successMessage,
  ].join("\n");
}

async function handleAnalyzeText() {
  const resultBox = document.getElementById("analysis-text-result");
  const mealText = document.getElementById("meal-text").value.trim();
  if (!mealText) {
    resultBox.textContent = t("describeMeal");
    return;
  }
  try {
    resultBox.textContent = t("analyzing");
    const day = document.getElementById("selected-day").value;
    const result = await analyzeMealText({ meal_text: mealText }, day);
    resultBox.textContent = showMacros(
      result,
      "total_calories",
      t("analysisComplete"),
    );
    document.getElementById("meal-text").value = "";
    window.dispatchEvent(new Event("calorie:day-updated"));
  } catch (error) {
    resultBox.textContent = error.message || t("analysisError");
  }
}

async function handleAnalyzeImage() {
  const resultBox = document.getElementById("analysis-image-result");
  const file = document.getElementById("image-file").files[0];
  const dish = document.getElementById("dish-name").value.trim();
  const grams = Number(document.getElementById("portion-grams").value);
  if (!file) {
    resultBox.textContent = t("selectImage");
    return;
  }
  if (!dish || !grams) {
    resultBox.textContent = t("enterDishAndWeight");
    return;
  }
  try {
    resultBox.textContent = t("analyzingImage");
    const day = document.getElementById("selected-day").value;
    const result = await analyzeMealImage(file, dish, grams, day);
    resultBox.textContent = showMacros(
      result,
      "estimated_calories",
      t("analysisComplete"),
    );
    document.getElementById("image-file").value = "";
    window.dispatchEvent(new Event("calorie:day-updated"));
  } catch (error) {
    resultBox.textContent = error.message || t("analysisError");
  }
}

export function bindNutritionEvents() {
  document
    .getElementById("analyze-text-btn")
    .addEventListener("click", handleAnalyzeText);
  document
    .getElementById("analyze-image-btn")
    .addEventListener("click", handleAnalyzeImage);
}
