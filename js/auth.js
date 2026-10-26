import { loginUser, registerUser, skipSignup } from "./api.js";
import { clearSession, saveSession, state } from "./session.js";
import { renderDashboard } from "./dashboard.js";

const authMessage = document.getElementById("auth-message");
const registerForm = document.getElementById("register-form");
const loginForm = document.getElementById("login-form");

function setStatus(message, type = "") {
  authMessage.textContent = message;
  authMessage.className = "status-message";
  if (type) authMessage.classList.add(type);
}

async function handleRegister(event) {
  event.preventDefault();
  const data = new FormData(registerForm);
  const payload = {
    name: String(data.get("name") || "").trim(),
    password: String(data.get("password") || ""),
    age: Number(data.get("age") || 0) || null,
    height: Number(data.get("height") || 0) || null,
    weight: Number(data.get("weight") || 0) || null,
  };
  if (!payload.name || !payload.password)
    return setStatus("Please fill in the required fields", "error");

  try {
    const result = await registerUser(payload);
    saveSession(result.token, result.user);
    setStatus("Account created", "success");
    renderDashboard(state.user);
  } catch (error) {
    setStatus(error.message || "Something went wrong", "error");
  }
}

async function handleLogin(event) {
  event.preventDefault();
  const data = new FormData(loginForm);
  const payload = {
    name: String(data.get("name") || "").trim(),
    password: String(data.get("password") || ""),
  };
  if (!payload.name || !payload.password)
    return setStatus("Please fill in all fields", "error");

  try {
    const result = await loginUser(payload);
    saveSession(result.token, result.user);
    setStatus("Login successful", "success");
    renderDashboard(state.user);
  } catch (error) {
    setStatus(error.message || "Something went wrong", "error");
  }
}

async function handleSkip() {
  const name = document.getElementById("register-name").value.trim();
  const password = document.getElementById("register-password").value;
  if (!name || !password)
    return setStatus("Add a name and password to continue", "error");

  try {
    const result = await skipSignup({ name, password });
    saveSession(result.token, result.user);
    setStatus(
      "You skipped extra data and started in a default mode",
      "success",
    );
    renderDashboard(state.user);
  } catch (error) {
    setStatus(error.message || "Unable to skip setup", "error");
  }
}

export function setAuthStatus(message, type = "") {
  setStatus(message, type);
}

export function bindAuthEvents() {
  registerForm.addEventListener("submit", handleRegister);
  loginForm.addEventListener("submit", handleLogin);
  document.getElementById("skip-btn").addEventListener("click", handleSkip);
  document.getElementById("logout-btn").addEventListener("click", () => {
    clearSession();
    setStatus("");
    renderDashboard(null);
  });
}
