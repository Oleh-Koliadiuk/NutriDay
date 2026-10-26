export const state = {
  token: localStorage.getItem("calorie_token") || "",
  user: null,
  lang: localStorage.getItem("calorie_lang") || "uk",
};

export function saveSession(token, user) {
  state.token = token;
  state.user = user;
  localStorage.setItem("calorie_token", token);
  localStorage.setItem("calorie_user", JSON.stringify(user));
}

export function clearSession() {
  state.token = "";
  state.user = null;
  localStorage.removeItem("calorie_token");
  localStorage.removeItem("calorie_user");
}
