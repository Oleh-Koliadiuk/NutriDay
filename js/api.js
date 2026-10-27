const API_BASE =
  window.location.port === "5500"
    ? `${window.location.protocol}//${window.location.hostname}:8000/api`
    : "/api";

async function apiRequest(path, options = {}) {
  const token = localStorage.getItem("calorie_token");
  const headers = new Headers(options.headers || {});

  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const text = await response.text();
  let payload = {};
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = { detail: text };
    }
  }

  if (!response.ok) {
    const detail = Array.isArray(payload.detail)
      ? payload.detail
          .map((issue) => issue.msg)
          .filter(Boolean)
          .join("; ")
      : payload.detail;
    const error = new Error(
      detail || payload.message || `Request failed (${response.status})`,
    );
    error.status = response.status;
    throw error;
  }
  return payload;
}

export const registerUser = (data) =>
  apiRequest("/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const loginUser = (data) =>
  apiRequest("/auth/login", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const skipSignup = (data) =>
  apiRequest("/auth/skip", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const getProfile = () => apiRequest("/auth/me");

export const updateProfile = (data) =>
  apiRequest("/auth/me", {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const forgotPassword = (email) =>
  apiRequest("/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email }),
  });

export const resetPassword = (email, code, newPassword) =>
  apiRequest("/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({ email, code, new_password: newPassword }),
  });

export const getDay = (day) =>
  apiRequest(`/nutrition/day?day=${encodeURIComponent(day)}`);

export const getHistory = () => apiRequest("/nutrition/history");

export const getDailyInsight = (day) =>
  apiRequest(`/nutrition/insight?day=${encodeURIComponent(day)}`, {
    method: "POST",
  });

export const updateMeal = (id, data) =>
  apiRequest(`/nutrition/meals/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const deleteMeal = (id) =>
  apiRequest(`/nutrition/meals/${id}`, { method: "DELETE" });

export const generateRecipe = (data) =>
  apiRequest("/recipes/generate", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const getRecipes = () => apiRequest("/recipes");

export const saveRecipe = (data) =>
  apiRequest("/recipes", { method: "POST", body: JSON.stringify(data) });

export const updateRecipe = (id, data) =>
  apiRequest(`/recipes/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const deleteRecipe = (id) =>
  apiRequest(`/recipes/${id}`, { method: "DELETE" });

export const analyzeMealText = (data, day) =>
  apiRequest(`/nutrition/analyze-text?day=${encodeURIComponent(day)}`, {
    method: "POST",
    body: JSON.stringify(data),
  });

export function analyzeMealImage(file, dishName, portionGrams, day) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("dish_name", dishName);
  formData.append("portion_grams", String(portionGrams));
  formData.append("day", day);
  return apiRequest("/nutrition/analyze-image", {
    method: "POST",
    body: formData,
  });
}
