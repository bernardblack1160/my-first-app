"""Keep the working app's tenant deposit and active state.

Revision ID: 0005_tenant_deposit_active
Revises: 0004_archive_settings
Create Date: 2026-09-09
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_tenant_deposit_active"
down_revision = "0004_archive_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("deposit", sa.Numeric(14, 2), server_default="0", nullable=False))
    op.add_column("tenants", sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False))


def downgrade() -> None:
    op.drop_column("tenants", "active")
    op.drop_column("tenants", "deposit")
