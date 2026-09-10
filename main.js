import { api } from "./api.js?v=9";
import { dashboard, detail, escapeHtml, expensesView, expenseForm, loginView, obligationForm, obligationPaymentForm, obligationsView, paymentForm, reportsView, shell, tenantForm } from "./components.js?v=9";

const app = document.querySelector("#app");
const modalRoot = document.querySelector("#modal-root");
const state = { user: null, tenants: [], expenses: [], obligations: [], summary: null, report: null, selected: null, view: "dashboard", booting: true, loginError: "" };

function isManager() {
  return state.user?.role === "manager" || state.user?.role === "admin";
}

function render() {
  if (state.booting) {
    app.innerHTML = `<main class="loading-screen"><div class="brand brand--center"><span class="brand-mark">ل</span><div><strong>lila</strong><span>در حال بارگذاری…</span></div></div></main>`;
    return;
  }
  if (!state.user) {
    app.innerHTML = loginView(state.loginError);
    return;
  }
  if (state.selected) {
    app.innerHTML = shell(detail(state.selected, state.user), state.user, true, "dashboard");
    return;
  }
  let content = dashboard(state.tenants, state.user, state.summary);
  if (state.view === "expenses") content = expensesView(state.expenses, state.user);
  if (state.view === "obligations") content = obligationsView(state.obligations, state.tenants, state.user);
  if (state.view === "reports") content = reportsView(state.report, state.user);
  app.innerHTML = shell(content, state.user, true, state.view);
}

function openModal(html) { modalRoot.innerHTML = html; }
function closeModal() { modalRoot.innerHTML = ""; }
function formPayload(form) { return Object.fromEntries(new FormData(form).entries()); }

function normalizeDigits(value) {
  const digits = "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩";
  return String(value ?? "").replace(/[۰-۹٠-٩]/g, (character) => {
    const index = digits.indexOf(character);
    return index < 10 ? String(index) : String(index - 10);
  });
}

function numeric(value) {
  return Number(normalizeDigits(value).replace(/[٬,\s]/g, "").replace("٫", "."));
}

function normalizedDate(value) {
  return normalizeDigits(value).trim().replace(/[.-]/g, "/").replace(/[^0-9/]/g, "");
}

function preparePayload(form) {
  const payload = formPayload(form);
  for (const key of ["monthly_rent", "penalty_rate_percent_per_day", "amount"]) {
    if (key in payload) payload[key] = numeric(payload[key]);
  }
  for (const key of ["contract_start", "paid_on", "spent_on", "due_date"]) {
    if (key in payload) payload[key] = normalizedDate(payload[key]);
  }
  return payload;
}

function requireDate(value) {
  if (!/^\d{4}\/\d{1,2}\/\d{1,2}$/.test(value)) throw new Error("تاریخ را مانند ۱۴۰۵/۰۱/۰۱ وارد کنید");
}

function requirePositive(value, label) {
  if (!Number.isFinite(value) || value <= 0) throw new Error(`${label} را درست وارد کنید`);
}

function showToast(message, danger = false) {
  const toast = document.createElement("div");
  toast.className = `toast ${danger ? "toast--danger" : ""}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3200);
}

async function loadData() {
  const [tenants, summary, expenses, obligations, report] = await Promise.all([api.listTenants(), api.dashboard(), api.listExpenses(), api.listObligations(), api.reportSummary()]);
  state.tenants = tenants;
  state.summary = summary;
  state.expenses = expenses;
  state.obligations = obligations;
  state.report = report;
  if (state.selected) state.selected = tenants.find((item) => item.id === state.selected.id) || null;
  render();
}

async function handleLogin(event) {
  event.preventDefault();
  try {
    state.loginError = "";
    state.user = (await api.login(formPayload(event.target))).user;
    state.view = "dashboard";
    state.booting = false;
    await loadData();
  } catch (error) {
    state.loginError = error.message;
    render();
  }
}

async function handleSubmit(event) {
  const form = event.target;
  if (!(form instanceof HTMLFormElement) || form.id === "login-form") return;
  event.preventDefault();
  try {
    if (form.id === "tenant-form") {
      const payload = preparePayload(form);
      requireDate(payload.contract_start);
      requirePositive(payload.monthly_rent, "اجاره ماهانه");
      const id = form.dataset.tenantId;
      const saved = id ? await api.updateTenant(id, payload) : await api.createTenant(payload);
      state.selected = id ? saved : null;
      closeModal();
      await loadData();
      showToast(id ? "اطلاعات مستأجر به‌روز شد" : "مستأجر ذخیره شد");
      return;
    }
    if (form.id === "payment-form") {
      const payload = preparePayload(form);
      requireDate(payload.paid_on);
      requirePositive(payload.amount, "مبلغ پرداختی");
      state.selected = await api.addPayment(state.selected.id, payload);
      closeModal();
      await loadData();
      showToast("پرداخت ثبت شد");
      return;
    }
    if (form.id === "expense-form") {
      const payload = preparePayload(form);
      requireDate(payload.spent_on);
      requirePositive(payload.amount, "مبلغ هزینه");
      await api.createExpense(payload);
      closeModal();
      await loadData();
      state.view = "expenses";
      render();
      showToast("هزینه ثبت شد");
      return;
    }
    if (form.id === "obligation-form") {
      const payload = preparePayload(form);
      requireDate(payload.due_date);
      requirePositive(payload.amount, "مبلغ تعهد");
      await api.createObligation(payload);
      closeModal();
      await loadData();
      state.view = "obligations";
      render();
      showToast("تعهد ثبت شد");
      return;
    }
    if (form.id === "obligation-payment-form") {
      const payload = preparePayload(form);
      requirePositive(payload.amount, "مبلغ پرداختی");
      await api.payObligation(form.dataset.obligationId, { amount: payload.amount });
      closeModal();
      await loadData();
      state.view = "obligations";
      render();
      showToast("پرداخت تعهد ثبت شد");
    }
  } catch (error) {
    showToast(error.message, true);
  }
}

document.addEventListener("submit", handleSubmit);
document.addEventListener("click", async (event) => {
  const viewButton = event.target.closest("[data-view]");
  if (viewButton) {
    state.view = viewButton.dataset.view;
    state.selected = null;
    render();
    return;
  }
  const viewAction = event.target.closest("[data-action^=\"view-\"]")?.dataset.action;
  if (viewAction) {
    state.view = viewAction.replace("view-", "");
    state.selected = null;
    render();
    return;
  }
  const tenantCard = event.target.closest("[data-tenant-id]");
  if (tenantCard && !event.target.closest("form")) {
    state.selected = state.tenants.find((item) => item.id === tenantCard.dataset.tenantId) || null;
    render();
    return;
  }
  const deleteExpense = event.target.closest("[data-action=\"delete-expense\"]");
  if (deleteExpense) {
    if (!isManager() || !window.confirm("این هزینه حذف شود؟")) return;
    try { await api.deleteExpense(deleteExpense.dataset.expenseId); await loadData(); showToast("هزینه حذف شد"); } catch (error) { showToast(error.message, true); }
    return;
  }
  const payObligation = event.target.closest("[data-action=\"pay-obligation\"]");
  if (payObligation) {
    const item = state.obligations.find((entry) => entry.id === payObligation.dataset.obligationId);
    if (item) {
      const modalHtml = obligationPaymentForm(item);
      const form = modalHtml.replace('<form id="obligation-payment-form"', `<form id="obligation-payment-form" data-obligation-id="${item.id}"`);
      openModal(form);
    }
    return;
  }
  const modal = event.target.closest(".modal");
  const modalAction = event.target.closest("[data-action]");
  if (modal && !modalAction) return;
  const action = event.target.closest("[data-action]")?.dataset.action;
  if (!action) return;
  if (action === "export-data") { window.location.assign("/api/export"); return; }
  if (action === "close-modal") { closeModal(); return; }
  if (action === "view-dashboard" || action === "view-expenses" || action === "view-obligations" || action === "view-reports") {
    state.view = action.replace("view-", "");
    state.selected = null;
    render();
    return;
  }
  if (action === "logout") {
    await api.logout().catch(() => {});
    state.user = null;
    state.selected = null;
    state.booting = false;
    render();
  }
  if (action === "new-tenant" && isManager()) openModal(tenantForm());
  if (action === "edit-tenant" && isManager() && state.selected) openModal(tenantForm(state.selected));
  if (action === "archive-tenant" && isManager() && state.selected && window.confirm("این مستأجر بایگانی شود؟")) {
    try { await api.archiveTenant(state.selected.id); state.selected = null; await loadData(); showToast("مستأجر بایگانی شد"); } catch (error) { showToast(error.message, true); }
  }
  if (action === "new-payment" && isManager() && state.selected) openModal(paymentForm());
  if (action === "new-expense" && isManager()) openModal(expenseForm());
  if (action === "new-obligation" && isManager()) {
    if (state.tenants.length) openModal(obligationForm(state.tenants));
    else showToast("ابتدا یک مستأجر ثبت کنید", true);
  }
  if (action === "back") { state.selected = null; render(); }
  if (action === "refresh") { loadData().catch((error) => showToast(error.message, true)); }
});

document.addEventListener("submit", (event) => {
  if (event.target.id === "login-form") handleLogin(event);
});

async function boot() {
  render();
  try {
    state.user = (await api.me()).user;
    state.booting = false;
    await loadData();
  } catch (error) {
    state.booting = false;
    if (error.status !== 401) state.loginError = "سرور در دسترس نیست؛ بعداً دوباره تلاش کنید.";
    render();
  }
}

if ("serviceWorker" in navigator && !window.LILA_DISABLE_SW) navigator.serviceWorker.register("/worker.js?v=9").catch(() => {});
boot();
