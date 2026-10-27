import {
  forgotPassword,
  loginUser,
  registerUser,
  resetPassword,
  skipSignup,
} from "./api.js";
import { clearSession, saveSession, state } from "./session.js";
import { renderDashboard } from "./dashboard.js";
import { t } from "./i18n.js";

const authMessage = document.getElementById("auth-message");
const registerForm = document.getElementById("register-form");
const loginForm = document.getElementById("login-form");
const recoveryDialog = document.getElementById("password-recovery-dialog");
const forgotPasswordForm = document.getElementById("forgot-password-form");
const resetPasswordForm = document.getElementById("reset-password-form");
let recoveryEmail = "";

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
    email: String(data.get("email") || "")
      .trim()
      .toLowerCase(),
    password: String(data.get("password") || ""),
    age: Number(data.get("age") || 0) || null,
    height: Number(data.get("height") || 0) || null,
    weight: Number(data.get("weight") || 0) || null,
  };
  if (!payload.name || !payload.email || !payload.password)
    return setStatus("Please fill in the required fields", "error");
  if (!document.getElementById("register-email").checkValidity())
    return setStatus(t("invalidForm"), "error");

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

async function requestPasswordReset(event) {
  event.preventDefault();
  const emailInput = document.getElementById("recovery-email");
  const submit = document.getElementById("send-reset-code");
  const status = document.getElementById("password-recovery-status");
  recoveryEmail = emailInput.value.trim().toLowerCase();
  submit.disabled = true;
  status.textContent = t("sendingResetCode");
  status.className = "recovery-status";
  console.info("[password recovery] form submitted", {
    origin: window.location.origin,
  });
  try {
    await forgotPassword(recoveryEmail);
    console.info("[password recovery] backend accepted the request");
    document.getElementById("recovery-email-summary").textContent =
      recoveryEmail;
    forgotPasswordForm.classList.add("hidden");
    resetPasswordForm.classList.remove("hidden");
    status.textContent = t("resetCodeSent");
    document.getElementById("reset-code").focus();
  } catch (error) {
    console.error("[password recovery] request failed", {
      status: error.status || null,
      message: error.message,
    });
    status.textContent =
      error.message === "email_service_not_configured"
        ? t("emailServiceNotConfigured")
        : t("passwordRecoveryError");
    status.classList.add("error");
  } finally {
    submit.disabled = false;
  }
}

async function submitPasswordReset(event) {
  event.preventDefault();
  const submit = document.getElementById("reset-password-submit");
  const status = document.getElementById("password-recovery-status");
  status.textContent = "";
  status.className = "recovery-status";
  submit.disabled = true;
  try {
    await resetPassword(
      recoveryEmail,
      document.getElementById("reset-code").value.trim(),
      document.getElementById("reset-new-password").value,
    );
    resetPasswordForm.reset();
    forgotPasswordForm.reset();
    resetPasswordForm.classList.add("hidden");
    forgotPasswordForm.classList.remove("hidden");
    status.textContent = t("passwordResetSuccess");
    status.classList.add("success");
    setAuthStatus(t("passwordResetSuccess"), "success");
    window.setTimeout(() => recoveryDialog.close(), 1300);
  } catch (error) {
    const message = {
      reset_code_invalid: t("resetCodeInvalid"),
      password_change_cooldown: t("passwordChangeTooSoon"),
      new_password_same: t("newPasswordSame"),
    }[error.message];
    status.textContent = message || t("passwordRecoveryError");
    status.classList.add("error");
  } finally {
    submit.disabled = false;
  }
}

function openPasswordRecovery() {
  forgotPasswordForm.reset();
  resetPasswordForm.reset();
  forgotPasswordForm.classList.remove("hidden");
  resetPasswordForm.classList.add("hidden");
  const status = document.getElementById("password-recovery-status");
  status.textContent = "";
  status.className = "recovery-status";
  recoveryDialog.showModal();
  document.getElementById("recovery-email").focus();
}

export function setAuthStatus(message, type = "") {
  setStatus(message, type);
}

export function bindAuthEvents() {
  registerForm.addEventListener("submit", handleRegister);
  loginForm.addEventListener("submit", handleLogin);
  document.getElementById("skip-btn").addEventListener("click", handleSkip);
  document
    .getElementById("forgot-password-btn")
    .addEventListener("click", openPasswordRecovery);
  document
    .getElementById("reset-password-from-settings")
    .addEventListener("click", () => {
      clearSession();
      setStatus("");
      renderDashboard(null);
      switchTab("login");
      openPasswordRecovery();
    });
  forgotPasswordForm.addEventListener("submit", requestPasswordReset);
  resetPasswordForm.addEventListener("submit", submitPasswordReset);
  document
    .getElementById("recovery-back-button")
    .addEventListener("click", () => {
      resetPasswordForm.classList.add("hidden");
      forgotPasswordForm.classList.remove("hidden");
      document.getElementById("password-recovery-status").textContent = "";
    });
  document.querySelectorAll("[data-recovery-close]").forEach((button) => {
    button.addEventListener("click", () => recoveryDialog.close());
  });
  document.getElementById("logout-btn").addEventListener("click", () => {
    clearSession();
    setStatus("");
    renderDashboard(null);
  });
}
