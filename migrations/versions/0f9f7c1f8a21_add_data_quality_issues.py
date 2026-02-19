"""add data quality issues table

Revision ID: 0f9f7c1f8a21
Revises: 5063c4cfd140
Create Date: 2026-02-13 16:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0f9f7c1f8a21"
down_revision: Union[str, Sequence[str], None] = "5063c4cfd140"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "data_quality_issues",
        sa.Column("check_name", sa.String(length=120), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column("competition_key", sa.String(length=60), nullable=True),
        sa.Column("entity_type", sa.String(length=60), nullable=False),
        sa.Column("entity_id", sa.String(length=120), nullable=True),
        sa.Column("issue_count", sa.Integer(), nullable=False),
        sa.Column("sample", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_data_quality_issues_check_name"), "data_quality_issues", ["check_name"], unique=False)
    op.create_index(op.f("ix_data_quality_issues_competition_key"), "data_quality_issues", ["competition_key"], unique=False)
    op.create_index(op.f("ix_data_quality_issues_run_id"), "data_quality_issues", ["run_id"], unique=False)
    op.create_index(op.f("ix_data_quality_issues_severity"), "data_quality_issues", ["severity"], unique=False)
    op.create_index(op.f("ix_data_quality_issues_source"), "data_quality_issues", ["source"], unique=False)
    op.create_index("ix_data_quality_main", "data_quality_issues", ["detected_at", "severity", "check_name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_data_quality_main", table_name="data_quality_issues")
    op.drop_index(op.f("ix_data_quality_issues_source"), table_name="data_quality_issues")
    op.drop_index(op.f("ix_data_quality_issues_severity"), table_name="data_quality_issues")
    op.drop_index(op.f("ix_data_quality_issues_run_id"), table_name="data_quality_issues")
    op.drop_index(op.f("ix_data_quality_issues_competition_key"), table_name="data_quality_issues")
    op.drop_index(op.f("ix_data_quality_issues_check_name"), table_name="data_quality_issues")
    op.drop_table("data_quality_issues")

