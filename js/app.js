import { getProfile } from "./api.js";
import { bindAuthEvents } from "./auth.js";
import { bindDashboardEvents, renderDashboard } from "./dashboard.js";
import { setLanguage } from "./i18n.js";
import { bindNutritionEvents } from "./nutrition.js";
import { clearSession, state } from "./session.js";
import { bindRecipeEvents } from "./recipes.js";

function switchTab(tab) {
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tab);
  });
  document
    .getElementById("register-form")
    .classList.toggle("active", tab === "register");
  document
    .getElementById("login-form")
    .classList.toggle("active", tab === "login");
}

async function bootstrapUser() {
  try {
    const savedUser = localStorage.getItem("calorie_user");
    state.user = savedUser ? JSON.parse(savedUser) : null;
  } catch {
    localStorage.removeItem("calorie_user");
    state.user = null;
  }

  if (state.token) {
    try {
      state.user = await getProfile();
      localStorage.setItem("calorie_user", JSON.stringify(state.user));
    } catch {
      clearSession();
    }
  }
  renderDashboard(state.user);
}

function bindEvents() {
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.addEventListener("click", () => switchTab(button.dataset.tab));
  });
  document.querySelectorAll("[data-language-select]").forEach((selector) => {
    selector.addEventListener("change", (event) => {
      state.lang = event.target.value;
      setLanguage(state.lang);
    });
  });
  const shell = document.querySelector(".page-shell");
  const sidebar = document.getElementById("account-sidebar");
  const sidebarToggle = document.getElementById("sidebar-toggle");
  const sidebarBackdrop = document.getElementById("sidebar-backdrop");
  const setSidebarOpen = (isOpen) => {
    shell.classList.toggle("sidebar-open", isOpen);
    sidebarToggle.setAttribute("aria-expanded", String(isOpen));
    sidebarToggle.setAttribute(
      "aria-label",
      isOpen ? "Закрити меню" : "Відкрити меню",
    );
    sidebar.inert = !isOpen;
  };
  sidebarToggle.addEventListener("click", () => {
    setSidebarOpen(sidebarToggle.getAttribute("aria-expanded") !== "true");
  });
  sidebarBackdrop.addEventListener("click", () => setSidebarOpen(false));
  sidebar.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener("click", () => setSidebarOpen(false));
  });
  document
    .getElementById("logout-btn")
    .addEventListener("click", () => setSidebarOpen(false));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") setSidebarOpen(false);
  });
  document.getElementById("current-year").textContent =
    new Date().getFullYear();
  bindAuthEvents();
  bindNutritionEvents();
  bindDashboardEvents();
  bindRecipeEvents();
}

bindEvents();
setLanguage(state.lang);
bootstrapUser();
