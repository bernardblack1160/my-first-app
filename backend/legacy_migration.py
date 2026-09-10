from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from .jalali import days_in_month, jalali_to_gregorian

KIND_TAG = re.compile(r"\[\s*(?:نوع|kind)\s*:\s*([^\]]+)\s*\]", re.IGNORECASE)
PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


@dataclass(frozen=True)
class MigrationIssue:
    table: str
    row_id: str
    message: str


def value(row: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in row and row[name] is not None:
            return row[name]
    return default


def require_uuid(row: dict[str, Any], table: str) -> UUID:
    raw = value(row, "id")
    if raw is None:
        raise ValueError("missing id")
    return UUID(str(raw))


def parse_amount(raw: Any) -> Decimal:
    if raw is None or raw == "":
        raise ValueError("missing amount")
    normalized = str(raw).replace(",", "").replace("٬", "").replace("٫", ".")
    try:
        return Decimal(normalized).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ValueError(f"invalid amount: {raw}") from exc


def parse_legacy_date_info(raw: Any) -> tuple[date, bool]:
    if raw is None or str(raw).strip() in {"", "—", "-"}:
        raise ValueError("missing Jalali date")
    normalized = str(raw).translate(PERSIAN_DIGITS).strip().replace("-", "/").replace(".", "/")
    parts = [int(part) for part in normalized.split("/") if part]
    partial = False
    if len(parts) == 1 and parts[0] >= 1000:
        year, month, day = parts[0], 1, 1
        partial = True
    elif len(parts) == 2 and parts[0] >= 1000:
        year, month, day = parts[0], parts[1], 1
        partial = True
    elif len(parts) == 3 and parts[0] >= 1000:
        year, month, day = parts
    elif len(parts) == 3 and parts[2] >= 1000:
        day, month, year = parts
    else:
        raise ValueError("تاریخ باید به شکل ۱۴۰۵/۰۱/۰۱ باشد")
    if month < 1 or month > 12 or day < 1 or day > days_in_month(year, month):
        raise ValueError("تاریخ شمسی معتبر نیست")
    return jalali_to_gregorian(year, month, day), partial


def parse_legacy_date(raw: Any) -> date:
    return parse_legacy_date_info(raw)[0]


def append_original_date(note: str, raw: Any, partial: bool) -> str:
    if not partial:
        return note
    original = str(raw or "").strip()
    marker = f"[تاریخ ناقص legacy: {original}]"
    return f"{note} {marker}".strip()


def split_tenant_name(raw: Any) -> tuple[str, str]:
    full = str(raw or "").strip()
    if not full:
        raise ValueError("missing tenant name")
    for separator in ("·", "|", " - "):
        if separator in full:
            unit, name = (part.strip() for part in full.split(separator, 1))
            if unit and name:
                return name[:160], unit[:80]
    return full[:160], "—"


def infer_transaction_kind(description: Any) -> str:
    text = str(description or "")
    match = KIND_TAG.search(text)
    if match:
        label = match.group(1).strip().lower()
        if label in {"ودیعه", "deposit"}:
            return "deposit"
        if label in {"سایر", "other"}:
            return "other"
        return "rent"
    if re.search(r"ودیعه|پول\s*پیش|رهن", text, re.IGNORECASE):
        return "deposit"
    if re.search(r"شارژ|تعمیر|هزینه|قبوض", text, re.IGNORECASE):
        return "other"
    return "rent"


def strip_kind_tag(description: Any) -> str:
    return KIND_TAG.sub("", str(description or "")).strip()


def boolean_value(raw: Any, default: bool = False) -> bool:
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() not in {"", "0", "false", "no", "none", "null"}


def map_tenant(row: dict[str, Any], workspace_id: UUID) -> dict[str, Any]:
    tenant_id = require_uuid(row, "tenants")
    name, unit = split_tenant_name(value(row, "name"))
    raw_date = value(row, "contract_date", "contract_start", "date")
    contract_start, partial = parse_legacy_date_info(raw_date)
    notes = append_original_date(str(value(row, "notes", default="") or ""), raw_date, partial)
    return {"id": tenant_id, "workspace_id": workspace_id, "name": name, "unit": unit, "contract_start": contract_start, "monthly_rent": parse_amount(value(row, "rent", "monthly_rent")), "deposit": parse_amount(value(row, "deposit", default=0)), "active": boolean_value(value(row, "active"), True), "penalty_rate_percent_per_day": Decimal("0.1"), "notes": notes}


def map_transaction(row: dict[str, Any], workspace_id: UUID, tenant_ids: set[UUID]) -> dict[str, Any]:
    transaction_id = require_uuid(row, "transactions")
    tenant_id = UUID(str(value(row, "tenant_id")))
    if tenant_id not in tenant_ids:
        raise ValueError(f"unknown tenant_id: {tenant_id}")
    raw_date = value(row, "date", "paid_on")
    transaction_date, partial = parse_legacy_date_info(raw_date)
    description = append_original_date(str(value(row, "description", "note", default="") or ""), raw_date, partial)
    return {"id": transaction_id, "workspace_id": workspace_id, "tenant_id": tenant_id, "date": transaction_date, "amount": parse_amount(value(row, "amount")), "description": strip_kind_tag(description), "kind": infer_transaction_kind(description), "show_in_report": boolean_value(value(row, "show_in_report"), True), "settled": boolean_value(value(row, "settled"), True), "type": str(value(row, "type", default="income") or "income"), "archived": boolean_value(value(row, "archived"), False)}


def map_expense(row: dict[str, Any], workspace_id: UUID) -> dict[str, Any]:
    expense_id = require_uuid(row, "expenses")
    raw_date = value(row, "date", "spent_on")
    date_value = None if raw_date is None or str(raw_date).strip() in {"", "—", "-"} else parse_legacy_date(raw_date)
    return {
        "id": expense_id,
        "workspace_id": workspace_id,
        "spent_on": date_value,
        "legacy_date_text": "" if date_value is not None else str(raw_date or "—"),
        "amount": parse_amount(value(row, "amount")),
        "category": str(value(row, "category", default="سایر") or "سایر")[:80],
        "note": str(value(row, "description", "note", default="") or ""),
        "show_in_report": boolean_value(value(row, "show_in_report"), True),
        "settled": boolean_value(value(row, "settled"), True),
        "type": str(value(row, "type", default="expense") or "expense"),
        "archived": boolean_value(value(row, "archived"), False),
    }


def map_archive(row: dict[str, Any], workspace_id: UUID) -> dict[str, Any]:
    archive_id = require_uuid(row, "archives")
    return {"id": archive_id, "workspace_id": workspace_id, "title": str(value(row, "title", default="آرشیو") or "آرشیو")[:160], "total_income": parse_amount(value(row, "total_income", default=0)), "total_expense": parse_amount(value(row, "total_expense", default=0)), "balance": parse_amount(value(row, "balance", default=0)), "items": value(row, "items", default={}) or {}}


def map_setting(row: dict[str, Any], workspace_id: UUID) -> dict[str, Any]:
    key = str(value(row, "key", default="") or "")[:160]
    if not key:
        raise ValueError("missing setting key")
    raw_id = value(row, "id")
    setting_id = UUID(str(raw_id)) if raw_id else uuid5(NAMESPACE_URL, f"lila-setting:{workspace_id}:{key}")
    return {"id": setting_id, "workspace_id": workspace_id, "key": key, "value": str(value(row, "value", default="") or "")}


def build_plan(dataset: dict[str, list[dict[str, Any]]], workspace_id: UUID) -> tuple[dict[str, list[dict[str, Any]]], list[MigrationIssue]]:
    plan: dict[str, list[dict[str, Any]]] = {key: [] for key in ("tenants", "transactions", "expenses", "archives", "settings")}
    issues: list[MigrationIssue] = []
    tenant_ids: set[UUID] = set()
    mappers = {"tenants": lambda row: map_tenant(row, workspace_id), "transactions": lambda row: map_transaction(row, workspace_id, tenant_ids), "expenses": lambda row: map_expense(row, workspace_id), "archives": lambda row: map_archive(row, workspace_id), "settings": lambda row: map_setting(row, workspace_id)}
    for table, mapper in mappers.items():
        for row in dataset.get(table, []):
            row_id = str(row.get("id", row.get("key", "?")))
            try:
                mapped = mapper(row)
                plan[table].append(mapped)
                if table == "tenants":
                    tenant_ids.add(mapped["id"])
            except (TypeError, ValueError, KeyError) as exc:
                issues.append(MigrationIssue(table, row_id, str(exc)))
    return plan, issues
