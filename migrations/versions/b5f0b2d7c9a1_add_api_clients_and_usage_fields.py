"""add api clients and usage fields

Revision ID: b5f0b2d7c9a1
Revises: a2b4d1ef0c31
Create Date: 2026-02-13 22:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b5f0b2d7c9a1"
down_revision: Union[str, Sequence[str], None] = "a2b4d1ef0c31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_clients",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("plan", sa.String(length=30), nullable=False),
        sa.Column("key_hash", sa.String(length=128), nullable=False),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_api_clients_is_active"), "api_clients", ["is_active"], unique=False)
    op.create_index(op.f("ix_api_clients_key_hash"), "api_clients", ["key_hash"], unique=True)
    op.create_index("ix_api_clients_plan_active", "api_clients", ["plan", "is_active"], unique=False)

    op.add_column("api_request_usage", sa.Column("api_client_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("api_request_usage", sa.Column("api_plan", sa.String(length=30), nullable=True))
    op.create_index(op.f("ix_api_request_usage_api_client_id"), "api_request_usage", ["api_client_id"], unique=False)
    op.create_index(op.f("ix_api_request_usage_api_plan"), "api_request_usage", ["api_plan"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_api_request_usage_api_plan"), table_name="api_request_usage")
    op.drop_index(op.f("ix_api_request_usage_api_client_id"), table_name="api_request_usage")
    op.drop_column("api_request_usage", "api_plan")
    op.drop_column("api_request_usage", "api_client_id")

    op.drop_index("ix_api_clients_plan_active", table_name="api_clients")
    op.drop_index(op.f("ix_api_clients_key_hash"), table_name="api_clients")
    op.drop_index(op.f("ix_api_clients_is_active"), table_name="api_clients")
    op.drop_table("api_clients")

