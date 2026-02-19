"""
People models: players, coaches, referees.
The 3 categories of individuals tracked in football data.
"""
import uuid
from typing import Optional
from datetime import date

from sqlalchemy import String, Integer, Float, ForeignKey, Date, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin


class Player(Base, UUIDMixin, TimestampMixin):
    """
    A football player.
    Central entity — everything revolves around player data.
    """
    __tablename__ = "players"

    # Identity
    name:            Mapped[str]           = mapped_column(String(200), nullable=False)
    full_name:       Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    date_of_birth:   Mapped[Optional[date]]= mapped_column(Date, nullable=True)
    nationality_id:  Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("countries.id"), nullable=True)

    # Physical / profile
    position:        Mapped[Optional[str]] = mapped_column(String(30), nullable=True)   # GK, CB, LB, RB, CDM, CM, CAM, LW, RW, CF, ST
    position_detail: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)   # more granular
    foot:            Mapped[Optional[str]] = mapped_column(String(10), nullable=True)   # left, right, both
    height_cm:       Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    weight_kg:       Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Media
    photo_url:       Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Status
    is_active:       Mapped[bool]          = mapped_column(Boolean, nullable=False, default=True)
    retired_at:      Mapped[Optional[date]]= mapped_column(Date, nullable=True)

    # External IDs — key for cross-referencing sources
    sofascore_id:     Mapped[Optional[int]] = mapped_column(Integer, nullable=True, unique=True, index=True)
    transfermarkt_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True, index=True)
    fbref_id:         Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    api_football_id:  Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    wikidata_id:      Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # Extra raw data (flexible JSONB for attributes we haven't modeled yet)
    extra:            Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    nationality:         Mapped[Optional["Country"]]        = relationship(back_populates="players")
    contracts:           Mapped[list["PlayerContract"]]     = relationship(back_populates="player", order_by="PlayerContract.start_date.desc()")
    market_values:       Mapped[list["MarketValue"]]        = relationship(back_populates="player", order_by="MarketValue.recorded_at.desc()")
    transfers:           Mapped[list["Transfer"]]           = relationship(back_populates="player", order_by="Transfer.transfer_date.desc()")
    match_stats:         Mapped[list["PlayerMatchStats"]]   = relationship(back_populates="player")
    match_events:        Mapped[list["MatchEvent"]]         = relationship(back_populates="player")

    def __repr__(self) -> str:
        return f"<Player {self.name} [{self.position}]>"


class Coach(Base, UUIDMixin, TimestampMixin):
    """
    Football manager / head coach.
    """
    __tablename__ = "coaches"

    name:            Mapped[str]           = mapped_column(String(200), nullable=False)
    date_of_birth:   Mapped[Optional[date]]= mapped_column(Date, nullable=True)
    nationality_id:  Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("countries.id"), nullable=True)
    photo_url:       Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active:       Mapped[bool]          = mapped_column(Boolean, nullable=False, default=True)

    sofascore_id:    Mapped[Optional[int]] = mapped_column(Integer, nullable=True, unique=True, index=True)
    transfermarkt_id:Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    nationality:   Mapped[Optional["Country"]]    = relationship()
    team_seasons:  Mapped[list["TeamSeason"]]      = relationship(back_populates="coach")

    def __repr__(self) -> str:
        return f"<Coach {self.name}>"


class Referee(Base, UUIDMixin, TimestampMixin):
    """
    Match referee.
    Referee data is underutilized but valuable for betting/analysis.
    Stats: avg cards per game, penalty rate, home bias, etc.
    """
    __tablename__ = "referees"

    name:           Mapped[str]           = mapped_column(String(200), nullable=False)
    date_of_birth:  Mapped[Optional[date]]= mapped_column(Date, nullable=True)
    nationality_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("countries.id"), nullable=True)
    is_active:      Mapped[bool]          = mapped_column(Boolean, nullable=False, default=True)

    sofascore_id:   Mapped[Optional[int]] = mapped_column(Integer, nullable=True, unique=True, index=True)

    # Relationships
    nationality: Mapped[Optional["Country"]] = relationship()
    matches:     Mapped[list["Match"]]        = relationship(back_populates="referee")

    def __repr__(self) -> str:
        return f"<Referee {self.name}>"
