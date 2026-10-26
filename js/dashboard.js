import {
  deleteMeal,
  getDay,
  getDailyInsight,
  getHistory,
  updateMeal,
  updateProfile,
} from "./api.js";
import { state } from "./session.js";
import { t } from "./i18n.js";

const authPanel = document.getElementById("auth-panel");
const dashboard = document.getElementById("dashboard");
const profileDialog = document.getElementById("profile-edit-dialog");
const mealDialog = document.getElementById("meal-edit-dialog");
let activeUser = null;
let selectedDay = localToday();
let currentDayData = null;
let editingField = "";
let editingMeal = null;

function localToday() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function formatNumber(value) {
  return new Intl.NumberFormat(state.lang, { maximumFractionDigits: 0 }).format(value || 0);
}

function renderProfile(user) {
  document.getElementById("welcome-name").textContent = user.name;
  document.getElementById("profile-name").textContent = user.name;
  document.getElementById("profile-age").textContent = user.age ?? "—";
  document.getElementById("profile-height").textContent = user.height ?? "—";
  document.getElementById("profile-weight").textContent = user.weight ?? "—";
  document.getElementById("profile-calorie-target").textContent = formatNumber(user.daily_calories);
  document.getElementById("protein-target").textContent = `${formatNumber(user.protein_goal)} g`;
  document.getElementById("carbs-target").textContent = `${formatNumber(user.carbs_goal)} g`;
  document.getElementById("fat-target").textContent = `${formatNumber(user.fat_goal)} g`;
}

export function renderDashboard(user) {
  if (!user) {
    activeUser = null;
    authPanel.classList.remove("hidden");
    dashboard.classList.add("hidden");
    return;
  }

  activeUser = user;
  renderProfile(user);
  authPanel.classList.add("hidden");
  dashboard.classList.remove("hidden");
  window.dispatchEvent(new Event("calorie:user-ready"));
  activatePage(location.hash.slice(1) || "profile");
  loadDashboardData();
}

function activatePage(page) {
  const availablePages = new Set(["profile", "records", "add", "recipe"]);
  const selectedPage = availablePages.has(page) ? page : "profile";
  document.querySelectorAll(".dashboard-page").forEach((section) => {
    section.classList.toggle("hidden", section.dataset.page !== selectedPage);
  });
  document.querySelectorAll("[data-page-link]").forEach((link) => {
    const isActive = link.dataset.pageLink === selectedPage;
    link.classList.toggle("active", isActive);
    if (isActive) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
}

async function loadDashboardData() {
  if (!activeUser) return;
  const dateInput = document.getElementById("selected-day");
  dateInput.value = selectedDay;
  dateInput.max = localToday();
  try {
    const [dayData, history] = await Promise.all([getDay(selectedDay), getHistory()]);
    currentDayData = dayData;
    renderDay(dayData);
    renderHistory(history);
  } catch (error) {
    document.getElementById("meal-list").textContent = error.message || t("loadError");
  }
}

function renderDay(day) {
  const isToday = day.day === localToday();
  document.getElementById("selected-day-title").textContent = isToday
    ? t("today")
    : new Intl.DateTimeFormat(state.lang, { dateStyle: "full" }).format(new Date(`${day.day}T12:00:00`));
  document.getElementById("calories-eaten").textContent = formatNumber(day.calories);
  document.getElementById("calories-target-label").textContent = formatNumber(day.calorie_target);
  const percent = day.calorie_target > 0 ? (day.calories / day.calorie_target) * 100 : 0;
  const progress = document.getElementById("calorie-progress");
  progress.style.width = `${Math.min(100, percent)}%`;
  progress.classList.toggle("over-target", percent > 100);
  progress.setAttribute("aria-valuenow", String(Math.min(100, Math.round(percent))));
  document.getElementById("calorie-progress-label").textContent = t("progressLabel", {
    percent: formatNumber(Math.round(percent)),
    remaining: formatNumber(Math.max(0, day.calorie_target - day.calories)),
  });
  document.getElementById("protein-eaten").textContent = `${formatNumber(day.protein)} g`;
  document.getElementById("carbs-eaten").textContent = `${formatNumber(day.carbs)} g`;
  document.getElementById("fat-eaten").textContent = `${formatNumber(day.fat)} g`;
  document.getElementById("daily-insight").textContent = day.insight || t("insightPlaceholder");
  renderMeals(day.meals || []);
}

function renderMeals(meals) {
  const list = document.getElementById("meal-list");
  list.replaceChildren();
  document.getElementById("meal-count-badge").textContent = String(meals.length);
  if (!meals.length) {
    const empty = document.createElement("li");
    empty.className = "empty-state";
    empty.textContent = t("noMeals");
    list.append(empty);
    return;
  }

  for (const meal of meals) {
    const item = document.createElement("li");
    item.className = "meal-row";
    const details = document.createElement("div");
    details.className = "meal-details";
    const heading = document.createElement("div");
    heading.className = "meal-title-row";
    const title = document.createElement("strong");
    title.textContent = meal.name;
    const source = document.createElement("span");
    source.className = "meal-source";
    source.textContent = t(meal.source === "image" ? "photoSource" : "textSource");
    heading.append(title, source);
    const description = document.createElement("p");
    description.textContent = meal.description || meal.summary || "";
    details.append(heading, description);

    const nutrition = document.createElement("div");
    nutrition.className = "meal-nutrition";
    const calories = document.createElement("strong");
    calories.textContent = `${formatNumber(meal.calories)} kcal`;
    const macros = document.createElement("span");
    macros.textContent = `Б ${formatNumber(meal.protein)} · В ${formatNumber(meal.carbs)} · Ж ${formatNumber(meal.fat)} g`;
    nutrition.append(calories, macros);

    const actions = document.createElement("div");
    actions.className = "meal-actions";
    const editButton = createIconButton("meal-edit", t("editMeal"));
    editButton.addEventListener("click", () => openMealEditor(meal));
    const deleteButton = createIconButton("meal-delete", t("deleteMeal"));
    deleteButton.addEventListener("click", async () => {
      deleteButton.disabled = true;
      try {
        await deleteMeal(meal.id);
        await loadDashboardData();
      } catch (error) {
        deleteButton.disabled = false;
        document.getElementById("daily-insight").textContent = error.message;
      }
    });
    actions.append(editButton, deleteButton);
    item.append(details, nutrition, actions);
    list.append(item);
  }
}

function createIconButton(className, label) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `icon-button ${className}`;
  button.setAttribute("aria-label", label);
  button.title = label;
  button.innerHTML = className.includes("delete")
    ? '<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M4.5 6h11m-9.5 0 .6 10h7l.6-10M8 6V4h4v2m-3 3v4m2-4v4" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    : '<svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="m12.8 4.2 3 3M4 16l3.4-.7 8.8-8.8a1.6 1.6 0 0 0-2.3-2.3l-8.8 8.8L4 16Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  return button;
}

function renderHistory(history) {
  const list = document.getElementById("history-list");
  list.replaceChildren();
  if (!history.length) {
    const empty = document.createElement("p");
    empty.className = "history-empty";
    empty.textContent = t("noHistory");
    list.append(empty);
    return;
  }
  for (const day of history) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `history-day${day.day === selectedDay ? " active" : ""}`;
    const date = document.createElement("span");
    date.textContent = new Intl.DateTimeFormat(state.lang, { month: "short", day: "numeric" }).format(new Date(`${day.day}T12:00:00`));
    const calories = document.createElement("strong");
    calories.textContent = `${formatNumber(day.calories)} / ${formatNumber(day.calorie_target)} kcal`;
    const meals = document.createElement("small");
    meals.textContent = t("mealCount", { count: day.meal_count });
    button.append(date, calories, meals);
    button.addEventListener("click", () => selectDay(day.day));
    list.append(button);
  }
}

function selectDay(day) {
  selectedDay = day;
  document.getElementById("selected-day").value = day;
  loadDashboardData();
}

function profileEditLabel(field) {
  return t(`editProfile${field[0].toUpperCase()}${field.slice(1)}`);
}

function openProfileEditor(field) {
  editingField = field;
  const input = document.getElementById("profile-edit-value");
  const label = document.getElementById("profile-edit-label");
  const fieldMap = {
    name: { type: "text", value: activeUser.name, min: "", max: "" },
    age: { type: "number", value: activeUser.age ?? "", min: "10", max: "120" },
    height: { type: "number", value: activeUser.height ?? "", min: "100", max: "260" },
    weight: { type: "number", value: activeUser.weight ?? "", min: "30", max: "300" },
  };
  const selected = fieldMap[field];
  label.textContent = profileEditLabel(field);
  input.type = selected.type;
  input.value = selected.value;
  input.min = selected.min;
  input.max = selected.max;
  input.step = field === "weight" ? "0.1" : "1";
  input.required = field === "name";
  profileDialog.showModal();
  input.focus();
}

function openMealEditor(meal) {
  editingMeal = meal;
  document.getElementById("meal-edit-name").value = meal.name;
  document.getElementById("meal-edit-description").value = meal.description || "";
  for (const field of ["calories", "protein", "carbs", "fat"]) {
    document.getElementById(`meal-edit-${field}`).value = meal[field];
  }
  mealDialog.showModal();
}

async function saveProfileEdit(event) {
  event.preventDefault();
  const input = document.getElementById("profile-edit-value");
  const value = editingField === "name" ? input.value.trim() : Number(input.value);
  if (!input.value.trim() || (editingField !== "name" && !Number.isFinite(value))) return;
  const saveButton = document.getElementById("profile-edit-save");
  saveButton.disabled = true;
  try {
    const user = await updateProfile({ [editingField]: value });
    state.user = user;
    localStorage.setItem("calorie_user", JSON.stringify(user));
    profileDialog.close();
    renderDashboard(user);
  } catch (error) {
    document.getElementById("profile-edit-error").textContent = error.message || t("saveError");
  } finally {
    saveButton.disabled = false;
  }
}

async function saveMealEdit(event) {
  event.preventDefault();
  if (!editingMeal) return;
  const payload = {
    name: document.getElementById("meal-edit-name").value.trim(),
    description: document.getElementById("meal-edit-description").value.trim(),
  };
  for (const field of ["calories", "protein", "carbs", "fat"]) {
    payload[field] = Number(document.getElementById(`meal-edit-${field}`).value);
  }
  const saveButton = document.getElementById("meal-edit-save");
  saveButton.disabled = true;
  try {
    await updateMeal(editingMeal.id, payload);
    mealDialog.close();
    editingMeal = null;
    await loadDashboardData();
  } catch (error) {
    document.getElementById("meal-edit-error").textContent = error.message || t("saveError");
  } finally {
    saveButton.disabled = false;
  }
}

async function generateInsight() {
  const button = document.getElementById("insight-button");
  const output = document.getElementById("daily-insight");
  button.disabled = true;
  output.textContent = t("insightLoading");
  try {
    await getDailyInsight(selectedDay);
    await loadDashboardData();
  } catch (error) {
    output.textContent = error.message || t("loadError");
  } finally {
    button.disabled = false;
  }
}

export function bindDashboardEvents() {
  document.querySelectorAll("[data-page-link]").forEach((link) => {
    link.addEventListener("click", () => activatePage(link.dataset.pageLink));
  });
  window.addEventListener("hashchange", () => {
    const page = location.hash.slice(1);
    if (activeUser && ["profile", "records", "add", "recipe"].includes(page)) {
      activatePage(page);
    }
  });
  document.querySelectorAll("[data-edit-field]").forEach((button) => {
    button.addEventListener("click", () => openProfileEditor(button.dataset.editField));
  });
  document.getElementById("selected-day").value = selectedDay;
  document.getElementById("selected-day").max = localToday();
  document.getElementById("selected-day").addEventListener("change", (event) => {
    if (event.target.value) selectDay(event.target.value);
  });
  document.getElementById("insight-button").addEventListener("click", generateInsight);
  document.getElementById("profile-edit-form").addEventListener("submit", saveProfileEdit);
  document.getElementById("meal-edit-form").addEventListener("submit", saveMealEdit);
  document.getElementById("profile-edit-value").addEventListener("input", () => {
    document.getElementById("profile-edit-error").textContent = "";
  });
  document.getElementById("meal-edit-form").addEventListener("input", () => {
    document.getElementById("meal-edit-error").textContent = "";
  });
  window.addEventListener("calorie:day-updated", () => loadDashboardData());
  window.addEventListener("calorie:language-changed", () => {
    document.querySelectorAll("[data-profile-label]").forEach((button) => {
      button.setAttribute("aria-label", t(button.dataset.profileLabel));
      button.title = t(button.dataset.profileLabel);
    });
    if (currentDayData) renderDay(currentDayData);
    if (activeUser) loadDashboardData();
  });
}
