export function money(value) {
  return new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 0 }).format(Number(value || 0));
}

export function number(value) {
  return new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 1 }).format(Number(value || 0));
}

export function statusLabel(status) {
  return { settled: "تسویه شد", overdue: "عقب‌افتاده", due: "سررسید شده" }[status] || status || "نامشخص";
}

export function statusClass(status) {
  return { settled: "status--good", overdue: "status--danger", due: "status--warning" }[status] || "status--muted";
}
