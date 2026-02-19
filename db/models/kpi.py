"""KPI persistence models for business observability."""
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UUIDMixin


class KPIDailySnapshot(Base, UUIDMixin):
    __tablename__ = "kpi_daily_snapshots"

    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    kpi_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    value: Mapped[Optional[float]] = mapped_column(nullable=True)
    tags: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_kpi_daily_unique", "snapshot_date", "kpi_name", unique=True),
    )


class APIRequestUsage(Base, UUIDMixin):
    __tablename__ = "api_request_usage"

    endpoint: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    status_code: Mapped[int] = mapped_column(nullable=False)
    api_client_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    api_plan: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, index=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
