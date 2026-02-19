"""add content priority reports

Revision ID: a2b4d1ef0c31
Revises: 9b2d1f3a7c44
Create Date: 2026-02-13 22:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a2b4d1ef0c31"
down_revision: Union[str, Sequence[str], None] = "9b2d1f3a7c44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "content_priority_reports",
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("window_days", sa.Integer(), nullable=False),
        sa.Column("target_min_ratio", sa.Float(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_content_priority_reports_report_date"), "content_priority_reports", ["report_date"], unique=False)
    op.create_index("ix_content_priority_report_unique", "content_priority_reports", ["report_date"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_content_priority_report_unique", table_name="content_priority_reports")
    op.drop_index(op.f("ix_content_priority_reports_report_date"), table_name="content_priority_reports")
    op.drop_table("content_priority_reports")

