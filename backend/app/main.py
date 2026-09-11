from datetime import date, datetime, timezone
import json
from decimal import Decimal
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .auth import AuthContext, create_session, normalize_email, require_auth, token_hash, verify_password
from .calculator import calculate_status
from .config import settings
from .db import get_db
from .jalali import JalaliError, format_jalali, gregorian_to_jalali, jalali_to_gregorian, parse_jalali
from .models import Archive, AuditLog, AuthSession, Expense, Membership, Obligation, Setting, Tenant, Transaction, User
from .schemas import (
    AuthResponse,
    DashboardSummary,
    ExpenseCreate,
    ExpenseSummary,
    HealthResponse,
    LoginRequest,
    ObligationCreate,
    ObligationPayment,
    ObligationSummary,
    PaymentCreate,
    PaymentSummary,
    ReportSummary,
    TenantCreate,
    TenantSummary,
    TenantUpdate,
    UserSummary,
)

app = FastAPI(title="Lila API", version="2.1.0")

_FIELD_LABELS = {
    "name": "نام مستأجر",
    "unit": "واحد / نشانی",
    "contract_start": "تاریخ شروع قرارداد",
    "monthly_rent": "اجاره ماهانه",
    "penalty_rate_percent_per_day": "درصد جریمه روزانه",
    "paid_on": "تاریخ پرداخت",
    "spent_on": "تاریخ هزینه",
    "due_date": "تاریخ تعهد",
    "amount": "مبلغ",
    "category": "دسته‌بندی",
    "tenant_id": "مستأجر",
}


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    location = first.get("loc", [])
    field = location[-1] if location else "اطلاعات فرم"
    label = _FIELD_LABELS.get(str(field), "اطلاعات فرم")
    message = first.get("msg", "مقدار نامعتبر")
    return JSONResponse(status_code=422, content={"detail": f"{label}: {message}"})


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)


def user_summary(context: AuthContext) -> UserSummary:
    return UserSummary(
        id=context.user.id,
        email=context.user.email,
        display_name=context.user.display_name,
        role=context.membership.role,
        workspace_name=context.membership.workspace.name,
    )


def auth_response(context: AuthContext) -> AuthResponse:
    return AuthResponse(user=user_summary(context))


def write_audit(db: Session, context: AuthContext, action: str, entity_type: str, entity_id: UUID | None = None, metadata: dict | None = None) -> None:
    db.add(
        AuditLog(
            workspace_id=context.membership.workspace_id,
            user_id=context.user.id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            metadata_json=metadata or {},
        )
    )


def require_manager(context: AuthContext = Depends(require_auth)) -> AuthContext:
    if context.membership.role not in {"manager", "admin"}:
        raise HTTPException(status_code=403, detail="این عملیات فقط برای مدیر مجاز است")
    return context


def get_tenant(db: Session, tenant_id: UUID, workspace_id: UUID) -> Tenant:
    tenant = db.scalar(
        select(Tenant)
        .options(selectinload(Tenant.transactions))
        .where(Tenant.id == tenant_id, Tenant.workspace_id == workspace_id, Tenant.archived_at.is_(None))
    )
    if not tenant:
        raise HTTPException(status_code=404, detail="مستاجر پیدا نشد")
    return tenant


def parse_user_date(value: str):
    try:
        return jalali_to_gregorian(*parse_jalali(value))
    except (JalaliError, ValueError, TypeError) as error:
        raise HTTPException(status_code=422, detail="تاریخ شمسی معتبر نیست؛ نمونه: ۱۴۰۵/۰۱/۰۱") from error


def make_summary(tenant: Tenant) -> TenantSummary:
    today_g = datetime.now(ZoneInfo("Asia/Tehran")).date()
    today_j = gregorian_to_jalali(today_g)
    start_j = gregorian_to_jalali(tenant.contract_start)
    payments = [(gregorian_to_jalali(item.date), item.amount) for item in tenant.transactions if not item.archived and item.kind == "rent"]
    result = calculate_status(
        contract_start=start_j,
        monthly_rent=tenant.monthly_rent,
        penalty_rate=tenant.penalty_rate_percent_per_day,
        payments=payments,
        today=today_j,
    )
    return TenantSummary(
        id=tenant.id,
        name=tenant.name,
        unit=tenant.unit,
        contract_start=format_jalali(start_j),
        monthly_rent=tenant.monthly_rent,
        deposit=tenant.deposit,
        active=tenant.active,
        penalty_rate_percent_per_day=tenant.penalty_rate_percent_per_day,
        notes=tenant.notes or "",
        today=format_jalali(today_j),
        payments=[PaymentSummary(id=item.id, paid_on=format_jalali(gregorian_to_jalali(item.date)), amount=item.amount, note=item.description or "") for item in tenant.transactions if not item.archived],
        **result,
    )


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.post("/api/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    email = normalize_email(payload.email)
    user = db.scalar(select(User).where(User.email == email))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="ایمیل یا رمز عبور نادرست است")
    membership = db.scalar(select(Membership).options(selectinload(Membership.workspace)).where(Membership.user_id == user.id).order_by(Membership.created_at))
    if not membership:
        raise HTTPException(status_code=403, detail="دسترسی به فضای کاری ندارید")
    context = AuthContext(user=user, membership=membership)
    token = create_session(db, user)
    db.commit()
    response.set_cookie(settings.session_cookie_name, token, max_age=settings.session_ttl_days * 86400, httponly=True, secure=settings.session_cookie_secure, samesite="lax", path="/")
    return auth_response(context)


@app.post("/api/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict[str, bool]:
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash(token)))
        if session:
            session.revoked_at = datetime.now(timezone.utc)
            db.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")
    return {"ok": True}


@app.get("/api/auth/me", response_model=AuthResponse)
def me(context: AuthContext = Depends(require_auth)) -> AuthResponse:
    return auth_response(context)


@app.get("/api/tenants", response_model=list[TenantSummary])
def list_tenants(context: AuthContext = Depends(require_auth), db: Session = Depends(get_db)) -> list[TenantSummary]:
    tenants = db.scalars(
        select(Tenant)
        .options(selectinload(Tenant.transactions))
        .where(Tenant.workspace_id == context.membership.workspace_id, Tenant.archived_at.is_(None))
        .order_by(Tenant.created_at, Tenant.name)
    ).all()
    return [make_summary(tenant) for tenant in tenants]


@app.post("/api/tenants", response_model=TenantSummary, status_code=201)
def create_tenant(payload: TenantCreate, context: AuthContext = Depends(require_manager), db: Session = Depends(get_db)) -> TenantSummary:
    tenant_data = payload.model_dump()
    tenant_data["contract_start"] = parse_user_date(tenant_data["contract_start"])
    tenant = Tenant(workspace_id=context.membership.workspace_id, **tenant_data)
    db.add(tenant)
    db.flush()
    write_audit(db, context, "create", "tenant", tenant.id, {"name": tenant.name, "unit": tenant.unit})
    db.commit()
    db.refresh(tenant)
    return make_summary(get_tenant(db, tenant.id, context.membership.workspace_id))


@app.patch("/api/tenants/{tenant_id}", response_model=TenantSummary)
def update_tenant(tenant_id: UUID, payload: TenantUpdate, context: AuthContext = Depends(require_manager), db: Session = Depends(get_db)) -> TenantSummary:
    tenant = get_tenant(db, tenant_id, context.membership.workspace_id)
    changes = payload.model_dump(exclude_unset=True)
    if "contract_start" in changes:
        changes["contract_start"] = parse_user_date(changes["contract_start"])
    for field, value in changes.items():
        setattr(tenant, field, value)
    write_audit(db, context, "update", "tenant", tenant.id, {"fields": list(changes)})
    db.commit()
    return make_summary(get_tenant(db, tenant.id, context.membership.workspace_id))


@app.delete("/api/tenants/{tenant_id}", status_code=204)
def archive_tenant(tenant_id: UUID, context: AuthContext = Depends(require_manager), db: Session = Depends(get_db)) -> Response:
    tenant = get_tenant(db, tenant_id, context.membership.workspace_id)
    tenant.archived_at = datetime.now(timezone.utc)
    write_audit(db, context, "archive", "tenant", tenant.id, {"name": tenant.name})
    db.commit()
    return Response(status_code=204)


@app.get("/api/tenants/{tenant_id}", response_model=TenantSummary)
def tenant_detail(tenant_id: UUID, context: AuthContext = Depends(require_auth), db: Session = Depends(get_db)) -> TenantSummary:
    return make_summary(get_tenant(db, tenant_id, context.membership.workspace_id))


@app.post("/api/tenants/{tenant_id}/payments", response_model=TenantSummary, status_code=201)
def add_payment(tenant_id: UUID, payload: PaymentCreate, context: AuthContext = Depends(require_manager), db: Session = Depends(get_db)) -> TenantSummary:
    tenant = get_tenant(db, tenant_id, context.membership.workspace_id)
    data = payload.model_dump()
    data["paid_on"] = parse_user_date(data["paid_on"])
    payment = Transaction(workspace_id=context.membership.workspace_id, tenant_id=tenant.id, date=data["paid_on"], amount=data["amount"], description=data.get("note", ""), kind="rent", type="income", show_in_report=True, settled=True, archived=False)
    db.add(payment)
    db.flush()
    write_audit(db, context, "create", "payment", payment.id, {"tenant_id": str(tenant.id), "amount": str(payment.amount)})
    db.commit()
    return make_summary(get_tenant(db, tenant.id, context.membership.workspace_id))


def expense_summary(item: Expense) -> ExpenseSummary:
    shown_date = format_jalali(gregorian_to_jalali(item.spent_on)) if item.spent_on else item.legacy_date_text or "—"
    return ExpenseSummary(id=item.id, spent_on=shown_date, amount=item.amount, category=item.category, note=item.note or "", show_in_report=item.show_in_report)


def obligation_summary(item: Obligation) -> ObligationSummary:
    remaining = max(Decimal("0"), item.amount - item.paid_amount)
    today = datetime.now(ZoneInfo("Asia/Tehran")).date()
    status = "paid" if remaining == 0 else "overdue" if item.due_date < today else "open"
    return ObligationSummary(id=item.id, tenant_id=item.tenant_id, tenant_name=item.tenant.name, title=item.title, due_date=format_jalali(gregorian_to_jalali(item.due_date)), amount=item.amount, paid_amount=item.paid_amount, remaining=remaining, note=item.note or "", status=status)


@app.get("/api/expenses", response_model=list[ExpenseSummary])
def list_expenses(context: AuthContext = Depends(require_auth), db: Session = Depends(get_db)) -> list[ExpenseSummary]:
    items = db.scalars(select(Expense).where(Expense.workspace_id == context.membership.workspace_id).order_by(Expense.spent_on.desc(), Expense.created_at.desc()).limit(100)).all()
    return [expense_summary(item) for item in items]


@app.post("/api/expenses", response_model=ExpenseSummary, status_code=201)
def create_expense(payload: ExpenseCreate, context: AuthContext = Depends(require_manager), db: Session = Depends(get_db)) -> ExpenseSummary:
    data = payload.model_dump()
    data["spent_on"] = parse_user_date(data["spent_on"])
    item = Expense(workspace_id=context.membership.workspace_id, **data)
    db.add(item)
    db.flush()
    write_audit(db, context, "create", "expense", item.id, {"amount": str(item.amount), "category": item.category})
    db.commit()
    return expense_summary(item)


@app.delete("/api/expenses/{expense_id}", status_code=204)
def delete_expense(expense_id: UUID, context: AuthContext = Depends(require_manager), db: Session = Depends(get_db)) -> Response:
    item = db.scalar(select(Expense).where(Expense.id == expense_id, Expense.workspace_id == context.membership.workspace_id))
    if not item:
        raise HTTPException(status_code=404, detail="هزینه پیدا نشد")
    write_audit(db, context, "delete", "expense", item.id, {"amount": str(item.amount)})
    db.delete(item)
    db.commit()
    return Response(status_code=204)


@app.get("/api/obligations", response_model=list[ObligationSummary])
def list_obligations(context: AuthContext = Depends(require_auth), db: Session = Depends(get_db)) -> list[ObligationSummary]:
    items = db.scalars(select(Obligation).options(selectinload(Obligation.tenant)).where(Obligation.workspace_id == context.membership.workspace_id).order_by(Obligation.due_date, Obligation.created_at)).all()
    return [obligation_summary(item) for item in items]


@app.post("/api/obligations", response_model=ObligationSummary, status_code=201)
def create_obligation(payload: ObligationCreate, context: AuthContext = Depends(require_manager), db: Session = Depends(get_db)) -> ObligationSummary:
    tenant = get_tenant(db, payload.tenant_id, context.membership.workspace_id)
    data = payload.model_dump()
    data["due_date"] = parse_user_date(data["due_date"])
    item = Obligation(workspace_id=context.membership.workspace_id, **data)
    db.add(item)
    db.flush()
    write_audit(db, context, "create", "obligation", item.id, {"tenant_id": str(tenant.id), "amount": str(item.amount)})
    db.commit()
    return obligation_summary(db.scalar(select(Obligation).options(selectinload(Obligation.tenant)).where(Obligation.id == item.id)))


@app.patch("/api/obligations/{obligation_id}/payment", response_model=ObligationSummary)
def pay_obligation(obligation_id: UUID, payload: ObligationPayment, context: AuthContext = Depends(require_manager), db: Session = Depends(get_db)) -> ObligationSummary:
    item = db.scalar(select(Obligation).options(selectinload(Obligation.tenant)).where(Obligation.id == obligation_id, Obligation.workspace_id == context.membership.workspace_id))
    if not item:
        raise HTTPException(status_code=404, detail="تعهد پیدا نشد")
    if item.paid_amount + payload.amount > item.amount:
        raise HTTPException(status_code=422, detail="مبلغ پرداختی از مانده تعهد بیشتر است")
    item.paid_amount += payload.amount
    write_audit(db, context, "payment", "obligation", item.id, {"amount": str(payload.amount)})
    db.commit()
    return obligation_summary(item)


@app.get("/api/dashboard", response_model=DashboardSummary)
def dashboard_summary(context: AuthContext = Depends(require_auth), db: Session = Depends(get_db)) -> DashboardSummary:
    tenants = db.scalars(select(Tenant).options(selectinload(Tenant.transactions)).where(Tenant.workspace_id == context.membership.workspace_id, Tenant.archived_at.is_(None))).all()
    summaries = [make_summary(item) for item in tenants]
    expenses = db.scalars(select(Expense).where(Expense.workspace_id == context.membership.workspace_id, Expense.archived.is_(False), Expense.show_in_report.is_(True)).order_by(Expense.spent_on.desc()).limit(5)).all()
    obligations = db.scalars(select(Obligation).options(selectinload(Obligation.tenant)).where(Obligation.workspace_id == context.membership.workspace_id).order_by(Obligation.due_date).limit(5)).all()
    return DashboardSummary(tenant_count=len(summaries), overdue_count=sum(item.status == "overdue" for item in summaries), balance=sum((item.balance for item in summaries), Decimal("0")), expenses_total=sum((item.amount for item in db.scalars(select(Expense).where(Expense.workspace_id == context.membership.workspace_id, Expense.archived.is_(False), Expense.show_in_report.is_(True))).all()), Decimal("0")), obligations_remaining=sum((max(Decimal("0"), item.amount - item.paid_amount) for item in obligations), Decimal("0")), recent_expenses=[expense_summary(item) for item in expenses], upcoming_obligations=[obligation_summary(item) for item in obligations])


@app.get("/api/reports/summary", response_model=ReportSummary)
def report_summary(context: AuthContext = Depends(require_auth), db: Session = Depends(get_db)) -> ReportSummary:
    tenants = db.scalars(select(Tenant).options(selectinload(Tenant.transactions)).where(Tenant.workspace_id == context.membership.workspace_id, Tenant.archived_at.is_(None))).all()
    expenses = db.scalars(select(Expense).where(Expense.workspace_id == context.membership.workspace_id, Expense.archived.is_(False), Expense.show_in_report.is_(True))).all()
    summaries = [make_summary(tenant) for tenant in tenants]
    total_due = sum((item.amount_due for item in summaries), Decimal("0"))
    total_paid = sum((item.amount_paid for item in summaries), Decimal("0"))
    total_balance = sum((item.balance for item in summaries), Decimal("0"))
    total_expenses = sum((item.amount for item in expenses), Decimal("0"))
    return ReportSummary(tenant_count=len(tenants), total_due=total_due, total_paid=total_paid, total_balance=total_balance, total_expenses=total_expenses, net_balance=total_paid - total_expenses, overdue_count=sum(1 for item in summaries if item.status == "overdue"))


@app.get("/api/export")
def export_data(context: AuthContext = Depends(require_auth), db: Session = Depends(get_db)) -> Response:
    tenants = db.scalars(select(Tenant).options(selectinload(Tenant.transactions)).where(Tenant.workspace_id == context.membership.workspace_id)).all()
    expenses = db.scalars(select(Expense).where(Expense.workspace_id == context.membership.workspace_id)).all()
    obligations = db.scalars(select(Obligation).where(Obligation.workspace_id == context.membership.workspace_id)).all()
    archives = db.scalars(select(Archive).where(Archive.workspace_id == context.membership.workspace_id)).all()
    settings_rows = db.scalars(select(Setting).where(Setting.workspace_id == context.membership.workspace_id)).all()
    payload = {
        "format": "lila-backup-v1",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "tenants": [{"id": str(item.id), "name": item.name, "unit": item.unit, "contract_start": str(item.contract_start), "monthly_rent": str(item.monthly_rent), "deposit": str(item.deposit), "active": item.active, "penalty_rate_percent_per_day": str(item.penalty_rate_percent_per_day), "notes": item.notes or "", "archived_at": item.archived_at.isoformat() if item.archived_at else None} for item in tenants],
        "payments": [{"id": str(item.id), "tenant_id": str(item.tenant_id), "date": str(item.date), "amount": str(item.amount), "description": item.description or "", "kind": item.kind, "show_in_report": item.show_in_report, "settled": item.settled, "type": item.type, "archived": item.archived} for tenant in tenants for item in tenant.transactions],
        "expenses": [{"id": str(item.id), "spent_on": str(item.spent_on) if item.spent_on else None, "legacy_date_text": item.legacy_date_text or "", "amount": str(item.amount), "category": item.category, "note": item.note or "", "show_in_report": item.show_in_report, "settled": item.settled, "type": item.type, "archived": item.archived} for item in expenses],
        "obligations": [{"id": str(item.id), "tenant_id": str(item.tenant_id), "title": item.title, "due_date": str(item.due_date), "amount": str(item.amount), "paid_amount": str(item.paid_amount), "note": item.note or ""} for item in obligations],
        "archives": [{"id": str(item.id), "title": item.title, "total_income": str(item.total_income), "total_expense": str(item.total_expense), "balance": str(item.balance), "items": item.items} for item in archives],
        "settings": [{"key": item.key, "value": item.value} for item in settings_rows],
    }
    return Response(content=json.dumps(payload, ensure_ascii=False), media_type="application/json", headers={"Content-Disposition": "attachment; filename=lila-backup.json"})
@app.get("/")
def read_root():
    return {"status": "backend is running", "database": "connected"}

@app.get("/api/health")
def health():
    return {"status": "ok"}
