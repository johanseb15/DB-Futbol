"""add sport mind tables

Revision ID: c8a3fce12e77
Revises: b5f0b2d7c9a1
Create Date: 2026-02-18 17:05:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c8a3fce12e77"
down_revision: Union[str, Sequence[str], None] = "b5f0b2d7c9a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostGIS is optional at migration time; this block won't fail on plain postgres image.
    op.execute(
        """
        DO $$
        BEGIN
          CREATE EXTENSION IF NOT EXISTS postgis;
        EXCEPTION
          WHEN undefined_file THEN
            RAISE NOTICE 'PostGIS extension not available in this PostgreSQL image.';
        END
        $$;
        """
    )

    op.create_table(
        "tracking_data",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("match_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("player_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("frame_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("frame_index", sa.Integer(), nullable=False),
        sa.Column("object_type", sa.String(length=16), nullable=False, server_default="player"),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("z", sa.Float(), nullable=True),
        sa.Column("speed_mps", sa.Float(), nullable=True),
        sa.Column("accel_mps2", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("object_type IN ('player','ball')", name="ck_tracking_data_object_type"),
    )
    op.create_index("ix_tracking_data_match_frame", "tracking_data", ["match_id", "frame_index"], unique=False)
    op.create_index("ix_tracking_data_player_ts", "tracking_data", ["player_id", "frame_ts"], unique=False)

    # Add geometry point column only if PostGIS is actually installed.
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis') THEN
            ALTER TABLE tracking_data
              ADD COLUMN position geometry(Point, 3857);
            CREATE INDEX IF NOT EXISTS ix_tracking_data_position_gist
              ON tracking_data USING GIST (position);
          END IF;
        END
        $$;
        """
    )

    op.create_table(
        "biometric_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("match_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("player_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("heart_rate_bpm", sa.Float(), nullable=True),
        sa.Column("hrv_rmssd", sa.Float(), nullable=True),
        sa.Column("workload_score", sa.Float(), nullable=True),
        sa.Column("sleep_hours", sa.Float(), nullable=True),
        sa.Column("cortisol_level", sa.Float(), nullable=True),
        sa.Column("source_device", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_biometric_logs_player_recorded_at", "biometric_logs", ["player_id", "recorded_at"], unique=False)
    op.create_index("ix_biometric_logs_match_player", "biometric_logs", ["match_id", "player_id"], unique=False)

    op.create_table(
        "event_context",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("match_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("player_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("pressure_level", sa.String(length=16), nullable=True),
        sa.Column("fatigue_perceived", sa.Float(), nullable=True),
        sa.Column("zone_code", sa.String(length=16), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_event_context_match_event_time", "event_context", ["match_id", "event_time"], unique=False)
    op.create_index("ix_event_context_event_type", "event_context", ["event_type"], unique=False)

    op.create_table(
        "injury_risk_factors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("player_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("week_start_date", sa.Date(), nullable=False),
        sa.Column("high_intensity_distance_m", sa.Float(), nullable=False, server_default="0"),
        sa.Column("acute_workload", sa.Float(), nullable=False, server_default="0"),
        sa.Column("chronic_workload", sa.Float(), nullable=False, server_default="0"),
        sa.Column("acute_chronic_ratio", sa.Float(), nullable=True),
        sa.Column("sleep_hours_avg", sa.Float(), nullable=True),
        sa.Column("cortisol_level_avg", sa.Float(), nullable=True),
        sa.Column("muscle_injury_next_7d", sa.Boolean(), nullable=True),
        sa.Column("model_risk_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", "week_start_date", name="uq_injury_risk_player_week"),
    )
    op.create_index("ix_injury_risk_factors_week", "injury_risk_factors", ["week_start_date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_injury_risk_factors_week", table_name="injury_risk_factors")
    op.drop_table("injury_risk_factors")

    op.drop_index("ix_event_context_event_type", table_name="event_context")
    op.drop_index("ix_event_context_match_event_time", table_name="event_context")
    op.drop_table("event_context")

    op.drop_index("ix_biometric_logs_match_player", table_name="biometric_logs")
    op.drop_index("ix_biometric_logs_player_recorded_at", table_name="biometric_logs")
    op.drop_table("biometric_logs")

    op.drop_index("ix_tracking_data_player_ts", table_name="tracking_data")
    op.drop_index("ix_tracking_data_match_frame", table_name="tracking_data")
    op.drop_table("tracking_data")
