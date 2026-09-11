from datetime import date
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import auth, calculator, config, db, jalali, models, schemas

settings = config.settings
app = FastAPI(title="Lila API", version="2.1.0")

_FIELD_LABELS = {
    "username": "نام کاربری",
    "password": "رمز عبور",
    "title": "عنوان",
    "amount": "مبلغ",
    "date": "تاریخ",
    "start_date": "تاریخ شروع",
    "due_day": "روز سررسید",
    "monthly_rent": "اجاره ماهانه",
    "deposit": "مبلغ ودیعه",
    "contract_end_date": "تاریخ پایان قرارداد",
    "active": "وضعیت فعال",
}


@app.exception_handler(RequestValidationError)
def validation_exception_handler(_: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else None
    field = first["loc"][-1] if first and first.get("loc") else "فیلد"
    label = _FIELD_LABELS.get(str(field), str(field))
    return JSONResponse(
        status_code=422,
        content={"detail": f"اطلاعات ورودی برای «{label}» نامعتبر است."},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def user_summary(user: models.User) -> schemas.UserSummary:
    return schemas.UserSummary(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        workspace_id=user.workspace_id,
    )


def auth_response(user: models.User, response: Response) -> schemas.AuthResponse:
    auth.set_session_cookie(response, user.id)
    return schemas.AuthResponse(user=user_summary(user))


def write_audit(
    session: Session,
    workspace_id: int,
    user_id: int,
    action: str,
    target_type: str,
    target_id: Optional[int] = None,
    details: Optional[str] = None,
):
    entry = models.AuditLog(
        workspace_id=workspace_id,
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
    )
    session.add(entry)


def require_manager(user: models.User = Depends(auth.get_current_user)) -> models.User:
    if user.role not in (models.Role.admin, models.Role.manager):
        raise HTTPException(status_code=403, detail="Manager access required")
    return user


def get_tenant(session: Session, workspace_id: int, tenant_id: int) -> models.Tenant:
    tenant = (
        session.query(models.Tenant)
        .filter(
            models.Tenant.workspace_id == workspace_id,
            models.Tenant.id == tenant_id,
            models.Tenant.archived_at.is_(None),
        )
        .first()
    )
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


def parse_user_date(val: Optional[str]) -> Optional[date]:
    if not val:
        return None
    return jalali.to_gregorian(val)


def make_summary(tenant: models.Tenant, today: Optional[date] = None) -> schemas.TenantSummary:
    payments = [
        calculator.PaymentRecord(
            amount=p.amount,
            paid_date=p.paid_date,
            kind=p.kind,
            period_start=p.period_start,
            period_end=p.period_end,
        )
        for p in tenant.payments
    ]
    ref_day = today or jalali.tehran_today()
    status_dict = calculator.calculate_status(
        start_date=tenant.start_date,
        due_day=tenant.due_day,
        monthly_rent=tenant.monthly_rent,
        deposit=tenant.deposit,
        payments=payments,
        today=ref_day,
        active=tenant.active,
        contract_end_date=tenant.contract_end_date,
    )
    return schemas.TenantSummary(
        id=tenant.id,
        name=tenant.name,
        monthly_rent=tenant.monthly_rent,
        deposit=tenant.deposit,
        start_date=tenant.start_date,
        due_day=tenant.due_day,
        contract_end_date=tenant.contract_end_date,
        active=tenant.active,
        **status_dict,
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/auth/login", response_model=schemas.AuthResponse)
def login(
    payload: schemas.LoginRequest,
    response: Response,
    session: Session = Depends(db.get_db),
):
    user = (
        session.query(models.User)
        .filter(models.User.username == payload.username.strip().lower())
        .first()
    )
    if not user or not auth.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not user.active:
        raise HTTPException(status_code=403, detail="User is inactive")
    return auth_response(user, response)


@app.post("/api/auth/logout")
def logout(response: Response):
    auth.clear_session_cookie(response)
    return {"ok": True}


@app.get("/api/auth/me", response_model=schemas.UserSummary)
def me(user: models.User = Depends(auth.get_current_user)):
    return user_summary(user)


@app.get("/api/tenants", response_model=List[schemas.TenantSummary])
def list_tenants(
    user: models.User = Depends(auth.get_current_user),
    session: Session = Depends(db.get_db),
):
    tenants = (
        session.query(models.Tenant)
        .filter(
            models.Tenant.workspace_id == user.workspace_id,
            models.Tenant.archived_at.is_(None),
        )
        .all()
    )
    return [make_summary(t) for t in tenants]


@app.post("/api/tenants", response_model=schemas.TenantSummary)
def create_tenant(
    payload: schemas.TenantCreate,
    user: models.User = Depends(require_manager),
    session: Session = Depends(db.get_db),
):
    tenant = models.Tenant(
        workspace_id=user.workspace_id,
        name=payload.name,
        monthly_rent=payload.monthly_rent,
        deposit=payload.deposit,
        start_date=parse_user_date(payload.start_date),
        due_day=payload.due_day,
        contract_end_date=parse_user_date(payload.contract_end_date),
        active=payload.active,
    )
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    write_audit(session, user.workspace_id, user.id, "create", "tenant", tenant.id)
    session.commit()
    return make_summary(tenant)


@app.patch("/api/tenants/{id}", response_model=schemas.TenantSummary)
def update_tenant(
    id: int,
    payload: schemas.TenantUpdate,
    user: models.User = Depends(require_manager),
    session: Session = Depends(db.get_db),
):
    tenant = get_tenant(session, user.workspace_id, id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field in ("start_date", "contract_end_date") and value is not None:
            value = parse_user_date(value)
        setattr(tenant, field, value)
    write_audit(session, user.workspace_id, user.id, "update", "tenant", tenant.id)
    session.commit()
    session.refresh(tenant)
    return make_summary(tenant)


@app.delete("/api/tenants/{id}")
def archive_tenant(
    id: int,
    user: models.User = Depends(require_manager),
    session: Session = Depends(db.get_db),
):
    tenant = get_tenant(session, user.workspace_id, id)
    tenant.archived_at = jalali.tehran_today()
    write_audit(session, user.workspace_id, user.id, "archive", "tenant", tenant.id)
    session.commit()
    return {"ok": True}


@app.get("/api/tenants/{id}", response_model=schemas.TenantSummary)
def get_tenant_detail(
    id: int,
    user: models.User = Depends(auth.get_current_user),
    session: Session = Depends(db.get_db),
):
    return make_summary(get_tenant(session, user.workspace_id, id))


@app.post("/api/tenants/{id}/payments", response_model=schemas.PaymentResponse)
def add_payment(
    id: int,
    payload: schemas.PaymentCreate,
    user: models.User = Depends(require_manager),
    session: Session = Depends(db.get_db),
):
    tenant = get_tenant(session, user.workspace_id, id)
    payment = models.Transaction(
        workspace_id=user.workspace_id,
        tenant_id=tenant.id,
        amount=payload.amount,
        paid_date=parse_user_date(payload.paid_date) or jalali.tehran_today(),
        kind="rent",
        note=payload.note,
    )
    session.add(payment)
    write_audit(
        session,
        user.workspace_id,
        user.id,
        "add_payment",
        "tenant",
        tenant.id,
        str(payload.amount),
    )
    session.commit()
    session.refresh(payment)
    return schemas.PaymentResponse(
        id=payment.id,
        tenant_id=tenant.id,
        amount=payment.amount,
        paid_date=payment.paid_date,
        kind=payment.kind,
        note=payment.note,
    )


@app.get("/api/expenses", response_model=List[schemas.ExpenseSummary])
def list_expenses(
    user: models.User = Depends(auth.get_current_user),
    session: Session = Depends(db.get_db),
):
    return (
        session.query(models.Expense)
        .filter(models.Expense.workspace_id == user.workspace_id)
        .order_by(models.Expense.date.desc())
        .limit(100)
        .all()
    )


@app.post("/api/expenses", response_model=schemas.ExpenseSummary)
def create_expense(
    payload: schemas.ExpenseCreate,
    user: models.User = Depends(require_manager),
    session: Session = Depends(db.get_db),
):
    expense = models.Expense(
        workspace_id=user.workspace_id,
        title=payload.title,
        amount=payload.amount,
        date=parse_user_date(payload.date) or jalali.tehran_today(),
        category=payload.category,
        note=payload.note,
    )
    session.add(expense)
    session.commit()
    session.refresh(expense)
    write_audit(session, user.workspace_id, user.id, "create", "expense", expense.id)
    session.commit()
    return expense


@app.delete("/api/expenses/{id}")
def delete_expense(
    id: int,
    user: models.User = Depends(require_manager),
    session: Session = Depends(db.get_db),
):
    expense = (
        session.query(models.Expense)
        .filter(
            models.Expense.workspace_id == user.workspace_id,
            models.Expense.id == id,
        )
        .first()
    )
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    session.delete(expense)
    write_audit(session, user.workspace_id, user.id, "delete", "expense", id)
    session.commit()
    return {"ok": True}


@app.get("/api/obligations", response_model=List[schemas.ObligationSummary])
def list_obligations(
    user: models.User = Depends(auth.get_current_user),
    session: Session = Depends(db.get_db),
):
    return (
        session.query(models.Obligation)
        .filter(models.Obligation.workspace_id == user.workspace_id)
        .all()
    )


@app.post("/api/obligations", response_model=schemas.ObligationSummary)
def create_obligation(
    payload: schemas.ObligationCreate,
    user: models.User = Depends(require_manager),
    session: Session = Depends(db.get_db),
):
    ob = models.Obligation(
        workspace_id=user.workspace_id,
        title=payload.title,
        amount=payload.amount,
        due_date=parse_user_date(payload.due_date),
        repeat_interval=payload.repeat_interval,
    )
    session.add(ob)
    session.commit()
    session.refresh(ob)
    write_audit(session, user.workspace_id, user.id, "create", "obligation", ob.id)
    session.commit()
    return ob


@app.patch("/api/obligations/{id}/payment", response_model=schemas.ObligationSummary)
def pay_obligation(
    id: int,
    payload: schemas.ObligationPayment,
    user: models.User = Depends(require_manager),
    session: Session = Depends(db.get_db),
):
    ob = (
        session.query(models.Obligation)
        .filter(
            models.Obligation.workspace_id == user.workspace_id,
            models.Obligation.id == id,
        )
        .first()
    )
    if not ob:
        raise HTTPException(status_code=404, detail="Obligation not found")
    if ob.paid_amount + payload.amount > ob.amount:
        raise HTTPException(status_code=400, detail="Payment exceeds remaining obligation")
    ob.paid_amount += payload.amount
    write_audit(
        session,
        user.workspace_id,
        user.id,
        "pay_obligation",
        "obligation",
        ob.id,
        str(payload.amount),
    )
    session.commit()
    session.refresh(ob)
    return ob


@app.get("/api/dashboard", response_model=schemas.DashboardSummary)
def dashboard(
    user: models.User = Depends(auth.get_current_user),
    session: Session = Depends(db.get_db),
):
    tenants = (
        session.query(models.Tenant)
        .filter(
            models.Tenant.workspace_id == user.workspace_id,
            models.Tenant.archived_at.is_(None),
        )
        .all()
    )
    summaries = [make_summary(t) for t in tenants]
    return calculator.build_dashboard_summary(summaries)


@app.get("/api/reports/summary", response_model=schemas.ReportSummary)
def report_summary(
    user: models.User = Depends(auth.get_current_user),
    session: Session = Depends(db.get_db),
):
    tenants = (
        session.query(models.Tenant)
        .filter(
            models.Tenant.workspace_id == user.workspace_id,
            models.Tenant.archived_at.is_(None),
        )
        .all()
    )
    summaries = [make_summary(t) for t in tenants]
    expenses = (
        session.query(models.Expense)
        .filter(models.Expense.workspace_id == user.workspace_id)
        .all()
    )
    return calculator.build_report_summary(summaries, expenses)


@app.get("/api/export")
def export_data(
    user: models.User = Depends(require_manager),
    session: Session = Depends(db.get_db),
):
    tenants = (
        session.query(models.Tenant)
        .filter(models.Tenant.workspace_id == user.workspace_id)
        .all()
    )
    expenses = (
        session.query(models.Expense)
        .filter(models.Expense.workspace_id == user.workspace_id)
        .all()
    )
    obligations = (
        session.query(models.Obligation)
        .filter(models.Obligation.workspace_id == user.workspace_id)
        .all()
    )
    return {
        "format": "lila-backup-v1",
        "tenants": [schemas.TenantExport.model_validate(t).model_dump() for t in tenants],
        "expenses": [schemas.ExpenseSummary.model_validate(e).model_dump() for e in expenses],
        "obligations": [schemas.ObligationSummary.model_validate(o).model_dump() for o in obligations],
    }


frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend_dir.exists() and (frontend_dir / "index.html").exists():

    @app.get("/", response_class=FileResponse)
    def serve_index():
        return FileResponse(
            frontend_dir / "index.html",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )

    @app.get("/sw.js", response_class=FileResponse)
    def serve_sw():
        return FileResponse(frontend_dir / "sw.js")

    @app.get("/manifest.webmanifest", response_class=FileResponse)
    def serve_manifest():
        return FileResponse(frontend_dir / "manifest.webmanifest")

    app.mount("/", StaticFiles(directory=str(frontend_dir)), name="frontend")
