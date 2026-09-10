import { money, number, statusClass, statusLabel } from "./format.js";

export function shell(content, user, connected = false, view = "dashboard") {
  const roleLabel = user?.role === "manager" || user?.role === "admin" ? "مدیر" : "مالک / مشاهده‌گر";
  const nav = `<nav class="topnav"><button class="nav-item ${view === "dashboard" ? "nav-item--active" : ""}" data-action="view-dashboard">نمای کلی</button><button class="nav-item ${view === "expenses" ? "nav-item--active" : ""}" data-action="view-expenses">هزینه‌ها</button><button class="nav-item ${view === "obligations" ? "nav-item--active" : ""}" data-action="view-obligations">تعهدات</button><button class="nav-item ${view === "reports" ? "nav-item--active" : ""}" data-action="view-reports">گزارش‌ها</button></nav>`;
  return `<div class="app-shell"><header class="topbar"><div class="brand"><span class="brand-mark">ل</span><div><strong>lila</strong><span>مدیریت اجاره</span></div></div>${nav}<div class="topbar-actions"><span class="user-chip">${escapeHtml(user?.display_name || "")} · ${roleLabel}</span><button class="logout" data-action="logout">خروج</button><div class="connection ${connected ? "connection--on" : ""}"><i></i>${connected ? "متصل" : "در حال اتصال"}</div></div></header><main class="page">${content}</main></div>`;
}

export function loginView(error = "") {
  return `<main class="login-page"><section class="login-card"><div class="brand brand--center"><span class="brand-mark">ل</span><div><strong>lila</strong><span>مدیریت اجاره</span></div></div><p class="eyebrow">ورود امن</p><h1>خوش آمدید</h1><p class="muted">برای دیدن اطلاعات ملک وارد حساب خود شوید.</p><form id="login-form" class="form"><label>ایمیل<input name="email" type="email" required autocomplete="username" dir="ltr" placeholder="you@example.com"></label><label>رمز عبور<input name="password" type="password" required minlength="8" autocomplete="current-password" dir="ltr"></label><button class="primary primary--full" type="submit">ورود</button></form>${error ? `<p class="form-error">${escapeHtml(error)}</p>` : ""}</section></main>`;
}

export function dashboard(tenants, user, summary = null) {
  const total = tenants.reduce((sum, item) => sum + Number(item.balance || 0), 0);
  const overdue = tenants.filter((item) => item.status === "overdue").length;
  const cards = tenants.map(tenantCard).join("");
  const manager = user?.role === "manager" || user?.role === "admin";
  const action = manager ? `<button class="primary" data-action="new-tenant">+ مستأجر جدید</button>` : `<span class="read-only-note">حساب شما فقط برای مشاهده است</span>`;
  const expenseTotal = summary ? summary.expenses_total : 0;
  const obligationTotal = summary ? summary.obligations_remaining : 0;
  return `<section class="hero"><div><p class="eyebrow">${escapeHtml(user?.workspace_name || "نمای کلی ملک")}</p><h1>سلام، ${escapeHtml(user?.display_name || "")}</h1><p class="muted">وضعیت اجاره‌ها را یک‌جا ببینید و به‌سادگی به‌روز کنید.</p></div>${action}</section><section class="stats"><div class="stat"><span>مستأجران</span><strong>${number(tenants.length)}</strong></div><div class="stat"><span>مانده کل</span><strong>${money(total)} <small>تومان</small></strong></div><div class="stat"><span>عقب‌افتاده</span><strong>${number(overdue)}</strong></div></section><div class="quick-grid"><button class="quick-card" data-action="view-expenses"><span>هزینه‌های ثبت‌شده</span><strong>${money(expenseTotal)} <small>تومان</small></strong><small>مدیریت هزینه‌های ملک ←</small></button><button class="quick-card" data-action="view-obligations"><span>مانده تعهدات</span><strong>${money(obligationTotal)} <small>تومان</small></strong><small>سررسیدها و پرداخت‌ها ←</small></button></div><section class="section-heading"><div><p class="eyebrow">پرتفوی اجاره</p><h2>مستأجران</h2></div><button class="ghost" data-action="refresh">به‌روزرسانی</button></section><div class="tenant-grid">${cards || emptyState(manager)}</div>`;
}

function tenantCard(tenant) {
  return `<button class="tenant-card" data-tenant-id="${tenant.id}"><div class="card-top"><span class="unit">${escapeHtml(tenant.unit || "بدون واحد")}</span><span class="status ${statusClass(tenant.status)}">${statusLabel(tenant.status)}</span></div><h3>${escapeHtml(tenant.name)}</h3><div class="card-finance"><span>مانده</span><strong>${money(tenant.balance)} <small>تومان</small></strong></div><div class="card-meta"><span>اجاره ماهانه ${money(tenant.monthly_rent)}</span><span>${tenant.days_late ? `${number(tenant.days_late)} روز تأخیر` : "به‌روز"}</span></div></button>`;
}

function emptyState(manager) {
  return `<div class="empty"><div class="empty-icon">＋</div><h3>هنوز مستأجری ثبت نشده</h3><p>${manager ? "اولین مستأجر را اضافه کنید تا وضعیت پرداخت‌ها را ببینید." : "هنوز اطلاعاتی برای نمایش ثبت نشده است."}</p>${manager ? `<button class="primary" data-action="new-tenant">افزودن مستأجر</button>` : ""}</div>`;
}

export function detail(tenant, user) {
  const manager = user?.role === "manager" || user?.role === "admin";
  const payments = tenant.payments.length ? tenant.payments.map((payment) => `<div class="payment-row"><div><strong>${payment.paid_on}</strong><span>${escapeHtml(payment.note || "پرداخت اجاره")}</span></div><strong>${money(payment.amount)} <small>تومان</small></strong></div>`).join("") : `<div class="empty empty--small"><p>هنوز پرداختی ثبت نشده است.</p></div>`;
  const paymentAction = manager ? `<button class="primary primary--full" data-action="new-payment">ثبت پرداخت</button>` : `<div class="read-only-note">نمایش اطلاعات پرداخت‌ها</div>`;
  const actions = manager ? `<div class="detail-actions"><button class="ghost" data-action="edit-tenant">ویرایش اطلاعات</button><button class="danger-button" data-action="archive-tenant">بایگانی مستأجر</button></div>` : "";
  return `<button class="back" data-action="back">← بازگشت به فهرست</button><section class="detail-head"><div><p class="eyebrow">${escapeHtml(tenant.unit || "مستأجر")}</p><h1>${escapeHtml(tenant.name)}</h1><p class="muted">شروع قرارداد: ${tenant.contract_start}</p></div><span class="status ${statusClass(tenant.status)} status--large">${statusLabel(tenant.status)}</span></section>${actions}<section class="detail-grid"><div class="balance-card"><span>مانده قابل پرداخت</span><strong>${money(tenant.balance)} <small>تومان</small></strong><div class="balance-lines"><span>کل سررسید <b>${money(tenant.amount_due)}</b></span><span>پرداخت‌شده <b>${money(tenant.amount_paid)}</b></span></div>${paymentAction}</div><div class="info-card"><div class="section-heading section-heading--tight"><h2>پرداخت‌ها</h2><span class="muted">${number(tenant.payments.length)} مورد</span></div>${payments}</div></section>${tenant.notes ? `<section class="note-card"><p class="eyebrow">یادداشت</p><p>${escapeHtml(tenant.notes)}</p></section>` : ""}`;
}

export function expensesView(expenses, user) {
  const manager = user?.role === "manager" || user?.role === "admin";
  const total = expenses.reduce((sum, item) => sum + Number(item.amount || 0), 0);
  const rows = expenses.length ? expenses.map((item) => `<div class="data-row"><div><strong>${escapeHtml(item.category)}</strong><span>${item.spent_on}${item.note ? ` · ${escapeHtml(item.note)}` : ""}</span></div><div class="row-end"><strong>${money(item.amount)} تومان</strong>${manager ? `<button class="icon-danger" data-action="delete-expense" data-expense-id="${item.id}" aria-label="حذف">×</button>` : ""}</div></div>`).join("") : `<div class="empty empty--small"><p>هنوز هزینه‌ای ثبت نشده است.</p></div>`;
  return `<section class="hero"><div><p class="eyebrow">دفتر مالی</p><h1>هزینه‌های ملک</h1><p class="muted">جمع ثبت‌شده: ${money(total)} تومان</p></div>${manager ? `<button class="primary" data-action="new-expense">+ ثبت هزینه</button>` : ""}</section><section class="info-card data-list">${rows}</section>`;
}

export function obligationsView(obligations, tenants, user) {
  const manager = user?.role === "manager" || user?.role === "admin";
  const rows = obligations.length ? obligations.map((item) => `<div class="data-row"><div><strong>${escapeHtml(item.title)}</strong><span>${escapeHtml(item.tenant_name)} · سررسید ${item.due_date}</span></div><div class="row-end"><div><strong>${money(item.remaining)} تومان</strong><span>${item.status === "paid" ? "تسویه شده" : `از ${money(item.amount)}`}</span></div>${manager && item.status !== "paid" ? `<button class="small-button" data-action="pay-obligation" data-obligation-id="${item.id}" data-remaining="${item.remaining}">پرداخت</button>` : ""}</div></div>`).join("") : `<div class="empty empty--small"><p>هنوز تعهدی ثبت نشده است.</p></div>`;
  return `<section class="hero"><div><p class="eyebrow">تعهدات و سررسیدها</p><h1>تعهدات ملک</h1><p class="muted">پرداخت‌های برنامه‌ریزی‌شده را کنار اجاره‌ها مدیریت کنید.</p></div>${manager && tenants.length ? `<button class="primary" data-action="new-obligation">+ ثبت تعهد</button>` : ""}</section><section class="info-card data-list">${rows}</section>`;
}

export function reportsView(report, user) {
  return `<section class="hero"><div><p class="eyebrow">گزارش مالی</p><h1>گزارش کلی ملک</h1><p class="muted">خلاصه وضعیت اجاره، هزینه‌ها و تعهدات.</p></div></section><section class="stats"><div class="stat"><span>اجاره دریافت‌شده</span><strong>${money(report?.total_paid)} <small>تومان</small></strong></div><div class="stat"><span>مانده اجاره</span><strong>${money(report?.total_balance)} <small>تومان</small></strong></div><div class="stat"><span>هزینه ملک</span><strong>${money(report?.total_expenses)} <small>تومان</small></strong></div></section><section class="info-card report-note"><p class="eyebrow">خالص دریافتی</p><p>${money(report?.net_balance)} تومان · ${number(report?.overdue_count)} مستأجر عقب‌افتاده از ${number(report?.tenant_count)} مستأجر</p></section>`;
}

export function tenantForm(tenant = null) {
  const editing = Boolean(tenant);
  return modal(editing ? "ویرایش مستأجر" : "مستأجر جدید", `<form id="tenant-form" class="form" data-tenant-id="${tenant?.id || ""}"><label>نام و نام خانوادگی<input name="name" required maxlength="160" value="${escapeHtml(tenant?.name || "")}" placeholder="مثلاً سارا احمدی"></label><label>واحد / نشانی<input name="unit" required maxlength="80" value="${escapeHtml(tenant?.unit || "")}" placeholder="مثلاً واحد ۳"></label><div class="form-row"><label>شروع قرارداد شمسی<input name="contract_start" required placeholder="۱۴۰۵/۰۱/۰۱" value="${tenant?.contract_start || "1405/01/01"}"></label><label>اجاره ماهانه<input name="monthly_rent" inputmode="numeric" required value="${tenant?.monthly_rent || ""}" placeholder="30000000"></label></div><label>درصد جریمه روزانه<input name="penalty_rate_percent_per_day" inputmode="decimal" value="${tenant?.penalty_rate_percent_per_day || "0"}"></label><label>یادداشت<textarea name="notes" rows="3" placeholder="یادداشت اختیاری">${escapeHtml(tenant?.notes || "")}</textarea></label><button class="primary primary--full" type="submit">${editing ? "ذخیره تغییرات" : "ذخیره مستأجر"}</button></form>`);
}

export function paymentForm() {
  return modal("ثبت پرداخت", `<form id="payment-form" class="form"><label>تاریخ پرداخت شمسی<input name="paid_on" required placeholder="۱۴۰۵/۰۱/۱۵" value="1405/01/15"></label><label>مبلغ پرداختی<input name="amount" inputmode="numeric" required placeholder="30000000"></label><label>توضیح<textarea name="note" rows="3" placeholder="مثلاً اجاره فروردین"></textarea></label><button class="primary primary--full" type="submit">ثبت پرداخت</button></form>`);
}

export function expenseForm() {
  return modal("ثبت هزینه", `<form id="expense-form" class="form"><label>تاریخ هزینه شمسی<input name="spent_on" required value="1405/01/01" placeholder="۱۴۰۵/۰۱/۰۱"></label><label>دسته‌بندی<input name="category" required value="تعمیرات" placeholder="مثلاً شارژ، تعمیرات، قبض"></label><label>مبلغ<input name="amount" inputmode="numeric" required placeholder="3000000"></label><label>توضیح<textarea name="note" rows="3" placeholder="توضیح اختیاری"></textarea></label><button class="primary primary--full" type="submit">ثبت هزینه</button></form>`);
}

export function obligationForm(tenants) {
  const options = tenants.map((tenant) => `<option value="${tenant.id}">${escapeHtml(tenant.name)} · ${escapeHtml(tenant.unit)}</option>`).join("");
  return modal("ثبت تعهد", `<form id="obligation-form" class="form"><label>مستأجر<select name="tenant_id" required>${options}</select></label><label>عنوان تعهد<input name="title" required maxlength="160" placeholder="مثلاً تعمیر کولر"></label><label>تاریخ سررسید شمسی<input name="due_date" required value="1405/01/15" placeholder="۱۴۰۵/۰۱/۱۵"></label><label>مبلغ<input name="amount" inputmode="numeric" required placeholder="3000000"></label><label>توضیح<textarea name="note" rows="3"></textarea></label><button class="primary primary--full" type="submit">ثبت تعهد</button></form>`);
}

export function obligationPaymentForm(obligation) {
  return modal("پرداخت تعهد", `<form id="obligation-payment-form" class="form"><p class="muted">مانده تعهد: ${money(obligation.remaining)} تومان</p><label>مبلغ پرداختی<input name="amount" inputmode="numeric" required value="${obligation.remaining}" max="${obligation.remaining}"></label><button class="primary primary--full" type="submit">ثبت پرداخت</button></form>`);
}

function modal(title, body) {
  return `<div class="modal-backdrop" data-action="close-modal"><div class="modal" role="dialog" aria-modal="true" aria-label="${escapeHtml(title)}"><button class="modal-close" data-action="close-modal">×</button><p class="eyebrow">lila</p><h2>${escapeHtml(title)}</h2>${body}</div></div>`;
}

export function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character]);
}
