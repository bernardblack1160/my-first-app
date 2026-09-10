const API_BASE = window.LILA_API_BASE || "/api";

function errorMessage(body) {
  if (typeof body?.detail === "string") return body.detail;
  if (Array.isArray(body?.detail)) {
    return body.detail.map((item) => {
      const field = Array.isArray(item.loc) ? item.loc.at(-1) : "فیلد";
      const labels = { name: "نام", unit: "واحد", contract_start: "شروع قرارداد", monthly_rent: "اجاره ماهانه", amount: "مبلغ", paid_on: "تاریخ پرداخت", spent_on: "تاریخ هزینه", due_date: "تاریخ سررسید" };
      return `${labels[field] || field}: مقدار واردشده معتبر نیست`;
    }).join("، ");
  }
  return "ارتباط با سرور انجام نشد؛ دوباره تلاش کنید.";
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  let body = null;
  try { body = text ? JSON.parse(text) : null; } catch { body = null; }
  if (!response.ok) {
    const error = new Error(errorMessage(body));
    error.status = response.status;
    throw error;
  }
  return body;
}

export const api = {
  me: () => request("/auth/me"),
  login: (payload) => request("/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  logout: () => request("/auth/logout", { method: "POST" }),
  listTenants: () => request("/tenants"),
  createTenant: (payload) => request("/tenants", { method: "POST", body: JSON.stringify(payload) }),
  updateTenant: (id, payload) => request(`/tenants/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  archiveTenant: (id) => request(`/tenants/${id}`, { method: "DELETE" }),
  getTenant: (id) => request(`/tenants/${id}`),
  addPayment: (id, payload) => request(`/tenants/${id}/payments`, { method: "POST", body: JSON.stringify(payload) }),
  dashboard: () => request("/dashboard"),
  listExpenses: () => request("/expenses"),
  createExpense: (payload) => request("/expenses", { method: "POST", body: JSON.stringify(payload) }),
  deleteExpense: (id) => request(`/expenses/${id}`, { method: "DELETE" }),
  listObligations: () => request("/obligations"),
  createObligation: (payload) => request("/obligations", { method: "POST", body: JSON.stringify(payload) }),
  payObligation: (id, payload) => request(`/obligations/${id}/payment`, { method: "PATCH", body: JSON.stringify(payload) }),
  reportSummary: () => request("/reports/summary"),
};
