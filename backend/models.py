from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Index, JSON, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    memberships: Mapped[list["Membership"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    tenants: Mapped[list["Tenant"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    expenses: Mapped[list["Expense"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    archives: Mapped[list["Archive"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    settings: Mapped[list["Setting"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    obligations: Mapped[list["Obligation"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    memberships: Mapped[list["Membership"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    sessions: Mapped[list["AuthSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (Index("ix_memberships_user_workspace", "user_id", "workspace_id", unique=True),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="owner", server_default="owner")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    workspace: Mapped[Workspace] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user: Mapped[User] = relationship(back_populates="sessions")


class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = (Index("ix_tenants_workspace_name", "workspace_id", "name"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    unit: Mapped[str] = mapped_column(String(80))
    contract_start: Mapped[date] = mapped_column(Date)
    monthly_rent: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    deposit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), server_default="0")
    active: Mapped[bool] = mapped_column(default=True, server_default="true")
    penalty_rate_percent_per_day: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0.1"), server_default="0.1")
    notes: Mapped[str] = mapped_column(Text, default="", server_default="")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    workspace: Mapped[Workspace] = relationship(back_populates="tenants")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="tenant", cascade="all, delete-orphan", order_by="Transaction.date")
    obligations: Mapped[list["Obligation"]] = relationship(back_populates="tenant", cascade="all, delete-orphan", order_by="Obligation.due_date")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (Index("ix_transactions_workspace_date", "workspace_id", "date"), Index("ix_transactions_tenant_date", "tenant_id", "date"))

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    kind: Mapped[str] = mapped_column(String(20), default="rent", server_default="rent")
    show_in_report: Mapped[bool] = mapped_column(default=True, server_default="true")
    settled: Mapped[bool] = mapped_column(default=True, server_default="true")
    type: Mapped[str] = mapped_column(String(20), default="income", server_default="income")
    archived: Mapped[bool] = mapped_column(default=False, server_default="false", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    workspace: Mapped[Workspace] = relationship(back_populates="transactions")
    tenant: Mapped[Tenant] = relationship(back_populates="transactions")


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (Index("ix_expenses_workspace_date", "workspace_id", "spent_on"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    spent_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    legacy_date_text: Mapped[str] = mapped_column(Text, default="", server_default="")
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    category: Mapped[str] = mapped_column(String(80), default="سایر", server_default="سایر")
    note: Mapped[str] = mapped_column(Text, default="", server_default="")
    show_in_report: Mapped[bool] = mapped_column(default=True, server_default="true", index=True)
    settled: Mapped[bool] = mapped_column(default=True, server_default="true")
    type: Mapped[str] = mapped_column(String(20), default="expense", server_default="expense")
    archived: Mapped[bool] = mapped_column(default=False, server_default="false", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    workspace: Mapped[Workspace] = relationship(back_populates="expenses")


class Obligation(Base):
    __tablename__ = "obligations"
    __table_args__ = (Index("ix_obligations_workspace_due_date", "workspace_id", "due_date"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    due_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), server_default="0")
    note: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    workspace: Mapped[Workspace] = relationship(back_populates="obligations")
    tenant: Mapped[Tenant] = relationship(back_populates="obligations")


class Archive(Base):
    __tablename__ = "archives"
    __table_args__ = (Index("ix_archives_workspace_title", "workspace_id", "title", unique=True),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    total_income: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), server_default="0")
    total_expense: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), server_default="0")
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"), server_default="0")
    items: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    workspace: Mapped[Workspace] = relationship(back_populates="archives")


class Setting(Base):
    __tablename__ = "settings"
    __table_args__ = (Index("ix_settings_workspace_key", "workspace_id", "key", unique=True),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(160))
    value: Mapped[str] = mapped_column(Text, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    workspace: Mapped[Workspace] = relationship(back_populates="settings")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(40))
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
