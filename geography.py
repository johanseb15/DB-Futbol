"""
Reference data models: geography and competition structure.
These change rarely and are the backbone of all other relations.
"""
import uuid
from typing import Optional

from sqlalchemy import String, Integer, ForeignKey, Boolean, Date, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin


class Country(Base, UUIDMixin, TimestampMixin):
    """
    Country reference table.
    Used for player nationalities, club origins, competition geography.
    """
    __tablename__ = "countries"

    name:       Mapped[str]           = mapped_column(String(100), nullable=False, unique=True)
    code_iso2:  Mapped[str]           = mapped_column(String(2),   nullable=False, unique=True)
    code_iso3:  Mapped[str]           = mapped_column(String(3),   nullable=True)
    continent:  Mapped[Optional[str]] = mapped_column(String(50),  nullable=True)
    flag_url:   Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    competitions: Mapped[list["Competition"]] = relationship(back_populates="country")
    teams:        Mapped[list["Team"]]        = relationship(back_populates="country")
    players:      Mapped[list["Player"]]      = relationship(back_populates="nationality")
    venues:       Mapped[list["Venue"]]       = relationship(back_populates="country")

    def __repr__(self) -> str:
        return f"<Country {self.code_iso2} — {self.name}>"


class Competition(Base, UUIDMixin, TimestampMixin):
    """
    Football competition (league, cup, international tournament).
    
    Scope: Argentina (all levels) + Top 5 European leagues + UCL.
    """
    __tablename__ = "competitions"
    __table_args__ = (
        UniqueConstraint("sofascore_id", name="uq_competition_sofascore"),
    )

    TYPES = ("league", "cup", "international", "friendly")

    name:              Mapped[str]           = mapped_column(String(200), nullable=False)
    short_name:        Mapped[Optional[str]] = mapped_column(String(50),  nullable=True)
    country_id:        Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("countries.id"), nullable=True)
    type:              Mapped[str]           = mapped_column(String(30),  nullable=False)  # league | cup | international
    level:             Mapped[int]           = mapped_column(Integer,     nullable=False, default=1)  # 1=primera, 2=segunda
    is_active:         Mapped[bool]          = mapped_column(Boolean,     nullable=False, default=True)

    # External IDs for cross-referencing
    sofascore_id:      Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    transfermarkt_id:  Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fbref_id:          Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    api_football_id:   Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    logo_url:          Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    country:  Mapped[Optional["Country"]] = relationship(back_populates="competitions")
    seasons:  Mapped[list["Season"]]      = relationship(back_populates="competition", order_by="Season.start_date.desc()")

    def __repr__(self) -> str:
        return f"<Competition {self.name}>"


class Season(Base, UUIDMixin, TimestampMixin):
    """
    A specific edition of a competition.
    Ex: Liga Profesional 2024, Premier League 2023/24.
    """
    __tablename__ = "seasons"
    __table_args__ = (
        UniqueConstraint("competition_id", "name", name="uq_season_competition_name"),
    )

    competition_id: Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("competitions.id"), nullable=False)
    name:           Mapped[str]            = mapped_column(String(50),  nullable=False)   # "2024", "2023/24"
    start_date:     Mapped[Optional[object]] = mapped_column(Date, nullable=True)
    end_date:       Mapped[Optional[object]] = mapped_column(Date, nullable=True)
    is_current:     Mapped[bool]           = mapped_column(Boolean, nullable=False, default=False)

    # Sofascore season ID (different from competition ID)
    sofascore_id:   Mapped[Optional[int]]  = mapped_column(Integer, nullable=True)

    # Relationships
    competition: Mapped["Competition"]      = relationship(back_populates="seasons")
    matches:     Mapped[list["Match"]]      = relationship(back_populates="season")

    def __repr__(self) -> str:
        return f"<Season {self.competition.name if self.competition else '?'} {self.name}>"


class Venue(Base, UUIDMixin, TimestampMixin):
    """
    Stadium / venue.
    """
    __tablename__ = "venues"

    name:        Mapped[str]            = mapped_column(String(200), nullable=False)
    city:        Mapped[Optional[str]]  = mapped_column(String(100), nullable=True)
    country_id:  Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("countries.id"), nullable=True)
    capacity:    Mapped[Optional[int]]  = mapped_column(Integer, nullable=True)
    latitude:    Mapped[Optional[float]] = mapped_column(nullable=True)
    longitude:   Mapped[Optional[float]] = mapped_column(nullable=True)

    sofascore_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    country: Mapped[Optional["Country"]] = relationship(back_populates="venues")
    matches: Mapped[list["Match"]]       = relationship(back_populates="venue")
    teams:   Mapped[list["Team"]]        = relationship(back_populates="home_venue")

    def __repr__(self) -> str:
        return f"<Venue {self.name}, {self.city}>"
