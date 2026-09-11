from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import auth, calculator, jalali, models, schemas
from .config import settings
from .db import Base, engine, get_db
from .seed import seed_initial_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        seed_initial_data(db)
    yield


app = FastAPI(
    title="Lila API",
    version="2.1.0",
    description="Backend API for Lila real-estate management system",
    lifespan=lifespan,
)

_FIELD_LABELS = {
    "title": "عنوان",
    "name": "نام",
    "unit_number": "شماره واحد",
    "rent_amount": "مبلغ اجاره",
    "deposit_amount": "مبلغ ودیعه",
    "amount": "مبلغ",
    "due_day": "روز سررسید",
    "start_date": "تاریخ شروع",
    "start_date_jalali": "تاریخ شروع",
    "end_date": "تاریخ پایان",
    "end_date_jalali": "تاریخ پایان",
    "due_date": "تاریخ سررسید",
    "due_date_jalali": "تاریخ سررسید",
    "date": "تاریخ",
    "date_jalali": "تاریخ",
    "paid_at": "تاریخ پرداخت",
    "paid_at_jalali": "تاریخ پرداخت",
    "phone": "شماره تماس",
    "category": "دسته‌بندی",
    "description": "توضیحات",
}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    errors = exc.errors()
    persian_messages = []
    for error in errors:
        loc = error.get("loc", ())
        field = loc[-1] if loc else "فیلد"
        field_name = _FIELD_LABELS.get(str(field), str(field))
        persian_messages.append(f"ورودی «{field_name}» نامعتبر است.")
    detail = " ".join(persian_messages) if persian_messages else "اطلاعات ارسالی نامعتبر است."
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": detail},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def user_summary(user: models.User, membership: models.Membership | None = None) -> schemas.UserSummary:
    role = membership.role if membership else "viewer"
    return schemas.UserSummary(
        id=user.id,
        phone=user.phone,
        full_name=user.full_name,
        role=role,
    )


def auth_response(user: models.User, session: models.AuthSession, membership: models.Membership | None, response: Response) -> schemas.AuthResponse:
    response.set_cookie(
        key=settings.cookie_name,
        value=session.session_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_days * 86400,
    )
    return schemas.AuthResponse(user=user_summary(user, membership), expires_at=session.expires_at)


def write_audit(db: Session, user: models.User, action: str, entity_name: str, entity_id: int | None, metadata: dict | None = None):
    audit = models.AuditLog(
        user_id=user.id,
        action=action,
        entity_name=entity_name,
        entity_id=entity_id,
        metadata_json=metadata or {},
    )
    db.add(audit)


def require_manager(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)) -> models.User:
    if not auth.is_manager(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="دسترسی غیرمجاز")
    return current_user


def get_tenant(db: Session, tenant_id: int) -> models.Tenant:
    tenant = db.get(models.Tenant, tenant_id)
    if not tenant or tenant.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="مستاجر یافت نشد")
    return tenant


def parse_user_date(jalali_str: str | None, gregorian_dt: datetime | None, field_name: str = "تاریخ") -> datetime:
    try:
        return jalali.parse_dual_date(jalali_str, gregorian_dt)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"فرمت {field_name} نامعتبر است.") from e


def make_summary(tenant: models.Tenant, db: Session, today: datetime | None = None) -> schemas.TenantSummary:
    now = today or datetime.now(ZoneInfo("Asia/Tehran"))
    payments = db.scalars(
        select(models.Transaction)
        .where(models.Transaction.tenant_id == tenant.id, models.Transaction.kind == "rent")
        .order_by(models.Transaction.paid_at.desc())
    ).all()
    history = [
        calculator.PaymentHistoryItem(
            paid_at=p.paid_at,
            amount=p.amount,
            period_year=p.period_year,
            period_month=p.period_month,
        )
        for p in payments
    ]
    status_calc = calculator.calculate_status(
        start_date=tenant.start_date,
        end_date=tenant.end_date,
        due_day=tenant.due_day,
        rent_amount=tenant.rent_amount,
        payments=history,
        today=now,
    )
    return schemas.TenantSummary(
        tenant=schemas.TenantOut.model_validate(tenant),
        status=status_calc,
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/auth/login", response_model=schemas.AuthResponse)
def login(payload: schemas.LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = auth.authenticate(db, payload.phone, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="شماره تماس یا رمز عبور اشتباه است")
    session = auth.create_session(db, user)
    membership = auth.get_membership(db, user)
    write_audit(db, user, "login", "user", user.id)
    db.commit()
    return auth_response(user, session, membership, response)


@app.post("/api/auth/logout")
def logout(response: Response, current_session: models.AuthSession = Depends(auth.get_current_session), db: Session = Depends(get_db)):
    auth.revoke_session(db, current_session)
    response.delete_cookie(key=settings.cookie_name)
    db.commit()
    return {"ok": True}


@app.get("/api/auth/me", response_model=schemas.UserSummary)
def me(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    membership = auth.get_membership(db, current_user)
    return user_summary(current_user, membership)


@app.get("/api/tenants", response_model=list[schemas.TenantSummary])
def list_tenants(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    tenants = db.scalars(
        select(models.Tenant)
        .where(models.Tenant.archived_at.is_(None))
        .order_by(models.Tenant.created_at.desc())
    ).all()
    return [make_summary(t, db) for t in tenants]


@app.post("/api/tenants", response_model=schemas.TenantSummary, status_code=status.HTTP_201_CREATED)
def create_tenant(payload: schemas.TenantCreate, current_user: models.User = Depends(require_manager), db: Session = Depends(get_db)):
    start_dt = parse_user_date(payload.start_date_jalali, payload.start_date, "تاریخ شروع")
    end_dt = parse_user_date(payload.end_date_jalali, payload.end_date, "تاریخ پایان")
    if end_dt <= start_dt:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="تاریخ پایان باید بعد از تاریخ شروع باشد")
    tenant = models.Tenant(
        name=payload.name,
        unit_number=payload.unit_number,
        phone=payload.phone,
        rent_amount=payload.rent_amount,
        deposit_amount=payload.deposit_amount,
        start_date=start_dt,
        end_date=end_dt,
        due_day=payload.due_day,
        notes=payload.notes,
    )
    db.add(tenant)
    db.flush()
    write_audit(db, current_user, "create", "tenant", tenant.id)
    db.commit()
    db.refresh(tenant)
    return make_summary(tenant, db)


@app.get("/api/tenants/{tenant_id}", response_model=schemas.TenantDetail)
def get_tenant_detail(tenant_id: int, current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    tenant = get_tenant(db, tenant_id)
    summary = make_summary(tenant, db)
    txs = db.scalars(
        select(models.Transaction)
        .where(models.Transaction.tenant_id == tenant.id)
        .order_by(models.Transaction.paid_at.desc())
    ).all()
    return schemas.TenantDetail(
        summary=summary,
        transactions=[schemas.TransactionOut.model_validate(t) for t in txs],
    )


@app.patch("/api/tenants/{tenant_id}", response_model=schemas.TenantSummary)
def update_tenant(tenant_id: int, payload: schemas.TenantUpdate, current_user: models.User = Depends(require_manager), db: Session = Depends(get_db)):
    tenant = get_tenant(db, tenant_id)
    update_data = payload.model_dump(exclude_unset=True)
    if "start_date_jalali" in update_data or "start_date" in update_data:
        tenant.start_date = parse_user_date(payload.start_date_jalali, payload.start_date, "تاریخ شروع")
    if "end_date_jalali" in update_data or "end_date" in update_data:
        tenant.end_date = parse_user_date(payload.end_date_jalali, payload.end_date, "تاریخ پایان")
    if tenant.end_date <= tenant.start_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="تاریخ پایان باید بعد از تاریخ شروع باشد")
    for key in ("name", "unit_number", "phone", "rent_amount", "deposit_amount", "due_day", "notes"):
        if key in update_data and update_data[key] is not None:
            setattr(tenant, key, update_data[key])
    write_audit(db, current_user, "update", "tenant", tenant.id)
    db.commit()
    db.refresh(tenant)
    return make_summary(tenant, db)


@app.delete("/api/tenants/{tenant_id}")
def archive_tenant(tenant_id: int, current_user: models.User = Depends(require_manager), db: Session = Depends(get_db)):
    tenant = get_tenant(db, tenant_id)
    tenant.archived_at = datetime.now(timezone.utc)
    write_audit(db, current_user, "archive", "tenant", tenant.id)
    db.commit()
    return {"ok": True}


@app.post("/api/tenants/{tenant_id}/payments", response_model=schemas.TransactionOut, status_code=status.HTTP_201_CREATED)
def record_payment(tenant_id: int, payload: schemas.PaymentCreate, current_user: models.User = Depends(require_manager), db: Session = Depends(get_db)):
    tenant = get_tenant(db, tenant_id)
    paid_dt = parse_user_date(payload.paid_at_jalali, payload.paid_at, "تاریخ پرداخت")
    tx = models.Transaction(
        tenant_id=tenant.id,
        amount=payload.amount,
        paid_at=paid_dt,
        period_year=payload.period_year,
        period_month=payload.period_month,
        note=payload.note,
        kind="rent",
        type="income",
    )
    db.add(tx)
    db.flush()
    write_audit(db, current_user, "payment", "tenant", tenant.id, {"amount": payload.amount})
    db.commit()
    db.refresh(tx)
    return schemas.TransactionOut.model_validate(tx)


def expense_summary(expense: models.Expense) -> schemas.ExpenseOut:
    return schemas.ExpenseOut.model_validate(expense)


def obligation_summary(ob: models.Obligation) -> schemas.ObligationOut:
    return schemas.ObligationOut.model_validate(ob)


@app.get("/api/expenses", response_model=list[schemas.ExpenseOut])
def list_expenses(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    expenses = db.scalars(
        select(models.Expense)
        .order_by(models.Expense.date.desc())
        .limit(100)
    ).all()
    return [expense_summary(e) for e in expenses]


@app.post("/api/expenses", response_model=schemas.ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(payload: schemas.ExpenseCreate, current_user: models.User = Depends(require_manager), db: Session = Depends(get_db)):
    dt = parse_user_date(payload.date_jalali, payload.date, "تاریخ")
    expense = models.Expense(
        title=payload.title,
        amount=payload.amount,
        date=dt,
        category=payload.category,
        description=payload.description,
    )
    db.add(expense)
    db.flush()
    write_audit(db, current_user, "create", "expense", expense.id)
    db.commit()
    db.refresh(expense)
    return expense_summary(expense)


@app.delete("/api/expenses/{expense_id}")
def delete_expense(expense_id: int, current_user: models.User = Depends(require_manager), db: Session = Depends(get_db)):
    expense = db.get(models.Expense, expense_id)
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="هزینه یافت نشد")
    db.delete(expense)
    write_audit(db, current_user, "delete", "expense", expense_id)
    db.commit()
    return {"ok": True}


@app.get("/api/obligations", response_model=list[schemas.ObligationOut])
def list_obligations(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    obs = db.scalars(
        select(models.Obligation)
        .order_by(models.Obligation.due_date.asc())
    ).all()
    return [obligation_summary(o) for o in obs]


@app.post("/api/obligations", response_model=schemas.ObligationOut, status_code=status.HTTP_201_CREATED)
def create_obligation(payload: schemas.ObligationCreate, current_user: models.User = Depends(require_manager), db: Session = Depends(get_db)):
    due_dt = parse_user_date(payload.due_date_jalali, payload.due_date, "تاریخ سررسید")
    ob = models.Obligation(
        title=payload.title,
        amount=payload.amount,
        due_date=due_dt,
        description=payload.description,
    )
    db.add(ob)
    db.flush()
    write_audit(db, current_user, "create", "obligation", ob.id)
    db.commit()
    db.refresh(ob)
    return obligation_summary(ob)


@app.patch("/api/obligations/{obligation_id}/payment", response_model=schemas.ObligationOut)
def record_obligation_payment(obligation_id: int, payload: schemas.ObligationPayment, current_user: models.User = Depends(require_manager), db: Session = Depends(get_db)):
    ob = db.get(models.Obligation, obligation_id)
    if not ob:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="تعهد یافت نشد")
    new_paid = ob.paid_amount + payload.amount
    if new_paid > ob.amount:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="مبلغ پرداختی بیشتر از مانده تعهد است")
    ob.paid_amount = new_paid
    if ob.paid_amount >= ob.amount:
        ob.status = "paid"
    write_audit(db, current_user, "payment", "obligation", ob.id, {"amount": payload.amount})
    db.commit()
    db.refresh(ob)
    return obligation_summary(ob)


@app.get("/api/dashboard", response_model=schemas.DashboardSummary)
def dashboard(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    tenants = db.scalars(select(models.Tenant).where(models.Tenant.archived_at.is_(None))).all()
    summaries = [make_summary(t, db) for t in tenants]
    recent_expenses = db.scalars(select(models.Expense).order_by(models.Expense.date.desc()).limit(5)).all()
    upcoming_obligations = db.scalars(
        select(models.Obligation)
        .where(models.Obligation.status != "paid")
        .order_by(models.Obligation.due_date.asc())
        .limit(5)
    ).all()
    return schemas.DashboardSummary(
        tenants_count=len(tenants),
        overdue_count=sum(1 for s in summaries if s.status.status == "overdue"),
        total_balance=sum(s.status.balance for s in summaries),
        recent_expenses=[expense_summary(e) for e in recent_expenses],
        upcoming_obligations=[obligation_summary(o) for o in upcoming_obligations],
    )


@app.get("/api/reports/summary", response_model=schemas.ReportSummary)
def reports_summary(current_user: models.User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    tenants = db.scalars(select(models.Tenant).where(models.Tenant.archived_at.is_(None))).all()
    summaries = [make_summary(t, db) for t in tenants]
    total_rent_income = sum(
        db.scalar(
            select(models.Transaction.amount)
            .where(models.Transaction.tenant_id == t.id, models.Transaction.kind == "rent")
        ) or 0
        for t in tenants
    )
    total_expenses = db.scalar(select(models.Expense.amount)) or 0
    return schemas.ReportSummary(
        total_income=total_rent_income,
        total_expenses=total_expenses,
        net_income=total_rent_income - total_expenses,
        tenant_summaries=summaries,
    )


@app.get("/api/export")
def export_data(current_user: models.User = Depends(require_manager), db: Session = Depends(get_db)):
    tenants = db.scalars(select(models.Tenant)).all()
    transactions = db.scalars(select(models.Transaction)).all()
    expenses = db.scalars(select(models.Expense)).all()
    obligations = db.scalars(select(models.Obligation)).all()
    data = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "tenants": [schemas.TenantOut.model_validate(t).model_dump(mode="json") for t in tenants],
        "transactions": [schemas.TransactionOut.model_validate(t).model_dump(mode="json") for t in transactions],
        "expenses": [schemas.ExpenseOut.model_validate(e).model_dump(mode="json") for e in expenses],
        "obligations": [schemas.ObligationOut.model_validate(o).model_dump(mode="json") for o in obligations],
    }
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": "attachment; filename=lila-backup.json"},
    )


def resolve_frontend_dir() -> Path | None:
    current_dir = Path(__file__).resolve().parent
    repo_root = current_dir.parents[1] if len(current_dir.parents) >= 2 else current_dir
    candidates = (
        repo_root / "frontend",
        repo_root,
        current_dir.parent / "frontend",
        current_dir.parent,
        current_dir / "frontend",
        current_dir,
        Path("/opt/render/project/src/frontend"),
        Path("/opt/render/project/src"),
    )
    for candidate in candidates:
        if (candidate / "index.html").is_file():
            return candidate
    return None


frontend_dir = resolve_frontend_dir()


if frontend_dir:
    @app.get("/", include_in_schema=False)
    def serve_root():
        return FileResponse(frontend_dir / "index.html", headers={"Cache-Control": "no-store, max-age=0"})

    @app.get("/worker.js", include_in_schema=False)
    def serve_worker():
        if (frontend_dir / "worker.js").is_file():
            return FileResponse(frontend_dir / "worker.js", headers={"Cache-Control": "no-store, max-age=0"})
        return Response(status_code=404)

    @app.get("/sw.js", include_in_schema=False)
    def serve_sw():
        if (frontend_dir / "sw.js").is_file():
            return FileResponse(frontend_dir / "sw.js", headers={"Cache-Control": "no-store, max-age=0"})
        return Response(status_code=404)

    @app.get("/manifest.webmanifest", include_in_schema=False)
    def serve_manifest():
        if (frontend_dir / "manifest.webmanifest").is_file():
            return FileResponse(frontend_dir / "manifest.webmanifest")
        return Response(status_code=404)

    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    @app.get("/", include_in_schema=False)
    def serve_root_fallback():
        return {"status": "ok", "message": "Backend running. Frontend files not found in root."}
