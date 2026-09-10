"""Preserve legacy expense dates and lifecycle state."""

from alembic import op
import sqlalchemy as sa

revision = "0007_preserve_expense_lifecycle"
down_revision = "0006_expense_report_visibility"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("expenses", "spent_on", existing_type=sa.Date(), nullable=True)
    op.add_column("expenses", sa.Column("legacy_date_text", sa.Text(), server_default="", nullable=False))
    op.add_column("expenses", sa.Column("settled", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column("expenses", sa.Column("type", sa.String(length=20), server_default="expense", nullable=False))
    op.add_column("expenses", sa.Column("archived", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_index("ix_expenses_archived", "expenses", ["archived"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_expenses_archived", table_name="expenses")
    op.drop_column("expenses", "archived")
    op.drop_column("expenses", "type")
    op.drop_column("expenses", "settled")
    op.drop_column("expenses", "legacy_date_text")
    op.alter_column("expenses", "spent_on", existing_type=sa.Date(), nullable=False)
