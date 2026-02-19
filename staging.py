"""
Staging / raw data tables.

Philosophy:
  1. Scrapers write raw JSON to `scrape_raw` — no transformation.
  2. Normalizer reads from `scrape_raw`, transforms, writes to clean tables.
  3. `scrape_jobs` tracks what has been scraped and when.

This decouples ingestion from transformation — we can always re-process
raw data without re-scraping, which is critical for rate-limited sources.
"""
import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, Text, Boolean, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UUIDMixin


class ScrapeJob(Base, UUIDMixin):
    """
    Tracks each scraping job — what was scraped, when, result.
    Enables idempotent re-runs and monitoring.
    """
    __tablename__ = "scrape_jobs"

    STATUSES = ("pending", "running", "success", "failed", "skipped")

    source:       Mapped[str]           = mapped_column(String(50),  nullable=False)   # "sofascore", "transfermarkt"
    entity_type:  Mapped[str]           = mapped_column(String(50),  nullable=False)   # "match", "player", "team"
    entity_id:    Mapped[str]           = mapped_column(String(100), nullable=False)   # source's ID (sofascore match id, etc.)
    url:          Mapped[Optional[str]] = mapped_column(String(1000),nullable=True)

    status:       Mapped[str]           = mapped_column(String(20),  nullable=False, default="pending", index=True)
    started_at:   Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at:  Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:   Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())

    http_status:  Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message:Mapped[Optional[str]] = mapped_column(Text,    nullable=True)
    retry_count:  Mapped[int]           = mapped_column(Integer, nullable=False, default=0)

    # After normalization
    normalized:   Mapped[bool]          = mapped_column(Boolean, nullable=False, default=False)
    normalized_at:Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_scrape_jobs_source_entity", "source", "entity_type", "entity_id"),
        Index("ix_scrape_jobs_status_created", "status", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ScrapeJob {self.source}/{self.entity_type}/{self.entity_id} [{self.status}]>"


class ScrapeRaw(Base, UUIDMixin):
    """
    Raw scraped data — JSON blobs before normalization.
    Never deleted, only appended. Immutable audit trail.
    """
    __tablename__ = "scrape_raw"

    job_id:       Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    source:       Mapped[str]           = mapped_column(String(50),  nullable=False, index=True)
    entity_type:  Mapped[str]           = mapped_column(String(50),  nullable=False, index=True)
    entity_id:    Mapped[str]           = mapped_column(String(100), nullable=False)

    # The raw payload — full API response or parsed page data
    payload:      Mapped[dict]          = mapped_column(JSONB, nullable=False)

    scraped_at:   Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        Index("ix_scrape_raw_source_entity_type", "source", "entity_type", "scraped_at"),
    )

    def __repr__(self) -> str:
        return f"<ScrapeRaw {self.source}/{self.entity_type}/{self.entity_id}>"
