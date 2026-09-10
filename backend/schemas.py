from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=200)


class UserSummary(BaseModel):
    id: UUID
    email: str
    display_name: str
    role: str
    workspace_name: str


class AuthResponse(BaseModel):
    user: UserSummary


class PaymentCreate(BaseModel):
    paid_on: str = Field(min_length=8, max_length=20)
    amount: Decimal = Field(gt=0)
    note: str = Field(default="", max_length=1000)


class PaymentSummary(BaseModel):
    id: UUID
    paid_on: str
    amount: Decimal
    note: str


class TenantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    unit: str = Field(min_length=1, max_length=80)
    contract_start: str = Field(min_length=8, max_length=20)
    monthly_rent: Decimal = Field(gt=0)
    deposit: Decimal = Field(default=Decimal("0"), ge=0)
    active: bool = True
    penalty_rate_percent_per_day: Decimal = Field(default=Decimal("0.1"), ge=0, le=100)
    notes: str = Field(default="", max_length=4000)


class TenantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    unit: str | None = Field(default=None, min_length=1, max_length=80)
    contract_start: str | None = Field(default=None, min_length=8, max_length=20)
    monthly_rent: Decimal | None = Field(default=None, gt=0)
    deposit: Decimal | None = Field(default=None, ge=0)
    active: bool | None = None
    penalty_rate_percent_per_day: Decimal | None = Field(default=None, ge=0, le=100)
    notes: str | None = Field(default=None, max_length=4000)


class TenantSummary(BaseModel):
    id: UUID
    name: str
    unit: str
    contract_start: str
    monthly_rent: Decimal
    deposit: Decimal
    active: bool
    penalty_rate_percent_per_day: Decimal
    notes: str
    today: str
    months_due: int
    amount_due: Decimal
    amount_paid: Decimal
    balance: Decimal
    days_late: int
    penalty: Decimal
    status: str
    last_event: str
    payments: list[PaymentSummary] = Field(default_factory=list)


class ExpenseCreate(BaseModel):
    spent_on: str = Field(min_length=8, max_length=20)
    amount: Decimal = Field(gt=0)
    category: str = Field(default="سایر", min_length=1, max_length=80)
    note: str = Field(default="", max_length=1000)
    show_in_report: bool = True


class ExpenseSummary(BaseModel):
    id: UUID
    spent_on: str
    amount: Decimal
    category: str
    note: str
    show_in_report: bool


class ObligationCreate(BaseModel):
    tenant_id: UUID
    title: str = Field(min_length=1, max_length=160)
    due_date: str = Field(min_length=8, max_length=20)
    amount: Decimal = Field(gt=0)
    note: str = Field(default="", max_length=1000)


class ObligationPayment(BaseModel):
    amount: Decimal = Field(gt=0)


class ObligationSummary(BaseModel):
    id: UUID
    tenant_id: UUID
    tenant_name: str
    title: str
    due_date: str
    amount: Decimal
    paid_amount: Decimal
    remaining: Decimal
    note: str
    status: str


class DashboardSummary(BaseModel):
    tenant_count: int
    overdue_count: int
    balance: Decimal
    expenses_total: Decimal
    obligations_remaining: Decimal
    recent_expenses: list[ExpenseSummary] = Field(default_factory=list)
    upcoming_obligations: list[ObligationSummary] = Field(default_factory=list)


class ReportSummary(BaseModel):
    tenant_count: int
    total_due: Decimal
    total_paid: Decimal
    total_balance: Decimal
    total_expenses: Decimal
    net_balance: Decimal
    overdue_count: int
