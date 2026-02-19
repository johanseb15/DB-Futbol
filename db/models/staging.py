import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, Boolean, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, UUIDMixin

class ScrapeJob(Base, UUIDMixin):
    __tablename__ = "scrape_jobs"
    source:        Mapped[str]            = mapped_column(String(50),   nullable=False)
    entity_type:   Mapped[str]            = mapped_column(String(50),   nullable=False)
    entity_id:     Mapped[str]            = mapped_column(String(100),  nullable=False)
    url:           Mapped[Optional[str]]  = mapped_column(String(1000), nullable=True)
    status:        Mapped[str]            = mapped_column(String(20),   nullable=False, default="pending", index=True)
    started_at:    Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at:   Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:    Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())
    http_status:   Mapped[Optional[int]]  = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]]  = mapped_column(Text,    nullable=True)
    retry_count:   Mapped[int]            = mapped_column(Integer, nullable=False, default=0)
    normalized:    Mapped[bool]           = mapped_column(Boolean, nullable=False, default=False)
    normalized_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (
        Index("ix_scrape_jobs_source_entity", "source", "entity_type", "entity_id"),
        Index("ix_scrape_jobs_status_created", "status", "created_at"),
    )

class ScrapeRaw(Base, UUIDMixin):
    __tablename__ = "scrape_raw"
    job_id:      Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    source:      Mapped[str]       = mapped_column(String(50),  nullable=False, index=True)
    entity_type: Mapped[str]       = mapped_column(String(50),  nullable=False, index=True)
    entity_id:   Mapped[str]       = mapped_column(String(100), nullable=False)
    payload:     Mapped[dict]      = mapped_column(JSONB,        nullable=False)
    scraped_at:  Mapped[datetime]  = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    __table_args__ = (Index("ix_scrape_raw_source_entity_type", "source", "entity_type", "scraped_at"),)
