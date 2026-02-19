"""add kpi tables

Revision ID: 9b2d1f3a7c44
Revises: 0f9f7c1f8a21
Create Date: 2026-02-13 19:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "9b2d1f3a7c44"
down_revision: Union[str, Sequence[str], None] = "0f9f7c1f8a21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_request_usage",
        sa.Column("endpoint", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_api_request_usage_category"), "api_request_usage", ["category"], unique=False)
    op.create_index(op.f("ix_api_request_usage_endpoint"), "api_request_usage", ["endpoint"], unique=False)
    op.create_index(op.f("ix_api_request_usage_requested_at"), "api_request_usage", ["requested_at"], unique=False)

    op.create_table(
        "kpi_daily_snapshots",
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("kpi_name", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_kpi_daily_snapshots_kpi_name"), "kpi_daily_snapshots", ["kpi_name"], unique=False)
    op.create_index(op.f("ix_kpi_daily_snapshots_snapshot_date"), "kpi_daily_snapshots", ["snapshot_date"], unique=False)
    op.create_index("ix_kpi_daily_unique", "kpi_daily_snapshots", ["snapshot_date", "kpi_name"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_kpi_daily_unique", table_name="kpi_daily_snapshots")
    op.drop_index(op.f("ix_kpi_daily_snapshots_snapshot_date"), table_name="kpi_daily_snapshots")
    op.drop_index(op.f("ix_kpi_daily_snapshots_kpi_name"), table_name="kpi_daily_snapshots")
    op.drop_table("kpi_daily_snapshots")

    op.drop_index(op.f("ix_api_request_usage_requested_at"), table_name="api_request_usage")
    op.drop_index(op.f("ix_api_request_usage_endpoint"), table_name="api_request_usage")
    op.drop_index(op.f("ix_api_request_usage_category"), table_name="api_request_usage")
    op.drop_table("api_request_usage")

