"""API clients and plans for commercial access control."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UUIDMixin


class APIClient(Base, UUIDMixin):
    __tablename__ = "api_clients"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    plan: Mapped[str] = mapped_column(String(30), nullable=False, default="free")
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_api_clients_plan_active", "plan", "is_active"),
    )

