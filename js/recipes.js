import {
  deleteRecipe,
  generateRecipe,
  getRecipes,
  saveRecipe,
  updateRecipe,
} from "./api.js";
import { state } from "./session.js";
import { t } from "./i18n.js";

let editingRecipeId = null;

const byId = (id) => document.getElementById(id);

function setStatus(id, message, type = "") {
  const element = byId(id);
  element.textContent = message;
  element.className = `recipe-status${type ? ` ${type}` : ""}`;
}

function ingredientRow(ingredient = {}) {
  const row = document.createElement("div");
  row.className = "recipe-ingredient-row";
  const name = document.createElement("input");
  name.type = "text";
  name.maxLength = 120;
  name.placeholder = t("recipeIngredientPlaceholder");
  name.value = ingredient.name || "";
  name.setAttribute("aria-label", t("recipeIngredientName"));
  const grams = document.createElement("input");
  grams.type = "number";
  grams.min = "0";
  grams.max = "10000";
  grams.step = "1";
  grams.value = ingredient.grams ?? "";
  grams.placeholder = t("recipeGramsPlaceholder");
  grams.setAttribute("aria-label", t("recipeIngredientGrams"));
  const note = document.createElement("input");
  note.type = "text";
  note.maxLength = 200;
  note.value = ingredient.note || "";
  note.placeholder = t("recipeNotePlaceholder");
  note.setAttribute("aria-label", t("recipeIngredientNote"));
  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "recipe-remove-button";
  remove.textContent = "×";
  remove.title = t("removeRecipeItem");
  remove.setAttribute("aria-label", t("removeRecipeItem"));
  remove.addEventListener("click", () => row.remove());
  row.append(name, grams, note, remove);
  return row;
}

function instructionRow(text = "") {
  const row = document.createElement("li");
  row.className = "recipe-step-row";
  const field = document.createElement("textarea");
  field.rows = 2;
  field.maxLength = 1000;
  field.value = text;
  field.placeholder = t("recipeStepPlaceholder");
  field.setAttribute("aria-label", t("recipeStepLabel"));
  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "recipe-remove-button";
  remove.textContent = "×";
  remove.title = t("removeRecipeItem");
  remove.setAttribute("aria-label", t("removeRecipeItem"));
  remove.addEventListener("click", () => row.remove());
  row.append(field, remove);
  return row;
}

function showRecipe(recipe, id = null) {
  editingRecipeId = id;
  byId("recipe-title").value = recipe.title || "";
  byId("recipe-description").value = recipe.description || "";
  byId("recipe-weight").value = recipe.total_weight_g || "";
  byId("recipe-servings").value = recipe.servings || 1;
  byId("recipe-calories").value = recipe.calories || 0;
  byId("recipe-protein").value = recipe.protein || 0;
  byId("recipe-carbs").value = recipe.carbs || 0;
  byId("recipe-fat").value = recipe.fat || 0;
  const ingredients = byId("recipe-ingredients");
  ingredients.replaceChildren(...(recipe.ingredients || []).map(ingredientRow));
  const instructions = byId("recipe-instructions");
  instructions.replaceChildren(
    ...(recipe.instructions || []).map(instructionRow),
  );
  byId("recipe-editor").classList.remove("hidden");
  byId("recipe-save-button").textContent = id
    ? t("recipeUpdateButton")
    : t("recipeSaveButton");
  setStatus("recipe-save-status", "");
  byId("recipe-editor").scrollIntoView({ behavior: "smooth", block: "start" });
}

function collectRecipe() {
  const ingredients = [
    ...byId("recipe-ingredients").querySelectorAll(".recipe-ingredient-row"),
  ]
    .map((row) => {
      const [name, grams, note] = row.querySelectorAll("input");
      return {
        name: name.value.trim(),
        grams: Number(grams.value),
        note: note.value.trim(),
      };
    })
    .filter((ingredient) => ingredient.name);
  const instructions = [
    ...byId("recipe-instructions").querySelectorAll("textarea"),
  ]
    .map((step) => step.value.trim())
    .filter(Boolean);
  return {
    title: byId("recipe-title").value.trim(),
    description: byId("recipe-description").value.trim(),
    total_weight_g: Number(byId("recipe-weight").value),
    servings: Number(byId("recipe-servings").value),
    ingredients,
    instructions,
    calories: Number(byId("recipe-calories").value),
    protein: Number(byId("recipe-protein").value),
    carbs: Number(byId("recipe-carbs").value),
    fat: Number(byId("recipe-fat").value),
  };
}

function renderSavedRecipes(recipes) {
  const list = byId("saved-recipe-list");
  list.replaceChildren();
  if (!recipes.length) {
    const empty = document.createElement("p");
    empty.className = "recipe-empty";
    empty.textContent = t("savedRecipesEmpty");
    list.append(empty);
    return;
  }
  for (const recipe of recipes) {
    const card = document.createElement("article");
    card.className = "saved-recipe-row";
    const open = document.createElement("button");
    open.type = "button";
    open.className = "saved-recipe-open";
    const title = document.createElement("strong");
    title.textContent = recipe.title;
    const meta = document.createElement("span");
    meta.textContent = `${recipe.total_weight_g} g · ${recipe.servings} ${t("recipeServingsShort")} · ${Math.round(recipe.calories)} kcal`;
    open.append(title, meta);
    open.addEventListener("click", () => showRecipe(recipe, recipe.id));
    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "recipe-remove-button saved-recipe-delete";
    remove.textContent = "×";
    remove.title = t("deleteRecipe");
    remove.setAttribute("aria-label", t("deleteRecipe"));
    remove.addEventListener("click", async () => {
      remove.disabled = true;
      try {
        await deleteRecipe(recipe.id);
        if (editingRecipeId === recipe.id) resetEditor();
        await loadSavedRecipes();
      } catch (error) {
        setStatus(
          "recipe-save-status",
          error.message || t("recipeSaveError"),
          "error",
        );
        remove.disabled = false;
      }
    });
    card.append(open, remove);
    list.append(card);
  }
}

export async function loadSavedRecipes() {
  try {
    renderSavedRecipes(await getRecipes());
  } catch (error) {
    setStatus(
      "recipe-save-status",
      error.message || t("recipeLoadError"),
      "error",
    );
  }
}

function resetEditor() {
  editingRecipeId = null;
  byId("recipe-editor").classList.add("hidden");
  byId("recipe-save-status").textContent = "";
}

async function handleGenerate() {
  const title = byId("recipe-request-title").value.trim();
  const weight = Number(byId("recipe-request-weight").value);
  const servings = Number(byId("recipe-request-servings").value);
  if (!title || !weight || !servings) {
    setStatus("recipe-generation-status", t("recipeFillRequired"), "error");
    return;
  }

  const button = byId("recipe-generate-button");
  button.disabled = true;
  setStatus("recipe-generation-status", t("recipeGenerating"));
  try {
    const recipe = await generateRecipe({
      title,
      target_weight_g: weight,
      servings,
      dietary_preferences: byId("recipe-request-preferences").value.trim(),
      language: state.lang,
    });
    showRecipe(recipe);
    setStatus("recipe-generation-status", t("recipeGenerated"), "success");
  } catch (error) {
    setStatus(
      "recipe-generation-status",
      error.message || t("recipeGenerateError"),
      "error",
    );
  } finally {
    button.disabled = false;
  }
}

async function handleSave() {
  const recipe = collectRecipe();
  if (
    !recipe.title ||
    !recipe.total_weight_g ||
    !recipe.servings ||
    !recipe.ingredients.length ||
    !recipe.instructions.length
  ) {
    setStatus("recipe-save-status", t("recipeFillRequired"), "error");
    return;
  }
  const button = byId("recipe-save-button");
  button.disabled = true;
  setStatus("recipe-save-status", t("recipeSaving"));
  try {
    const saved = editingRecipeId
      ? await updateRecipe(editingRecipeId, recipe)
      : await saveRecipe(recipe);
    showRecipe(saved, saved.id);
    setStatus("recipe-save-status", t("recipeSaved"), "success");
    await loadSavedRecipes();
  } catch (error) {
    setStatus(
      "recipe-save-status",
      error.message || t("recipeSaveError"),
      "error",
    );
  } finally {
    button.disabled = false;
  }
}

export function bindRecipeEvents() {
  byId("recipe-generate-button").addEventListener("click", handleGenerate);
  byId("recipe-save-button").addEventListener("click", handleSave);
  byId("recipe-add-ingredient").addEventListener("click", () =>
    byId("recipe-ingredients").append(ingredientRow()),
  );
  byId("recipe-add-step").addEventListener("click", () =>
    byId("recipe-instructions").append(instructionRow()),
  );
  byId("recipe-new-button").addEventListener("click", resetEditor);
  window.addEventListener("calorie:user-ready", loadSavedRecipes);
  window.addEventListener("calorie:language-changed", () => {
    byId("recipe-save-button").textContent = editingRecipeId
      ? t("recipeUpdateButton")
      : t("recipeSaveButton");
    if (state.user) loadSavedRecipes();
  });
}
