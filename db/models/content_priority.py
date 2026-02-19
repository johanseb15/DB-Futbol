"""Persisted editorial priority reports for content analytics."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Index, Integer, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UUIDMixin


class ContentPriorityReport(Base, UUIDMixin):
    __tablename__ = "content_priority_reports"

    report_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    window_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    target_min_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_content_priority_report_unique", "report_date", unique=True),
    )

