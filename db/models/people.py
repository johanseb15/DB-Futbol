import uuid
from typing import Optional
from datetime import date
from sqlalchemy import String, Integer, Float, ForeignKey, Date, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin, UUIDMixin

class Player(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "players"
    name:            Mapped[str]           = mapped_column(String(200), nullable=False)
    full_name:       Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    date_of_birth:   Mapped[Optional[date]]= mapped_column(Date, nullable=True)
    nationality_id:  Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("countries.id"), nullable=True)
    position:        Mapped[Optional[str]] = mapped_column(String(30),  nullable=True)
    position_detail: Mapped[Optional[str]] = mapped_column(String(50),  nullable=True)
    foot:            Mapped[Optional[str]] = mapped_column(String(10),  nullable=True)
    height_cm:       Mapped[Optional[int]] = mapped_column(Integer,     nullable=True)
    weight_kg:       Mapped[Optional[int]] = mapped_column(Integer,     nullable=True)
    photo_url:       Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active:       Mapped[bool]          = mapped_column(Boolean,     nullable=False, default=True)
    retired_at:      Mapped[Optional[date]]= mapped_column(Date,        nullable=True)
    sofascore_id:     Mapped[Optional[int]] = mapped_column(Integer,     nullable=True, unique=True, index=True)
    transfermarkt_id: Mapped[Optional[str]] = mapped_column(String(50),  nullable=True, unique=True, index=True)
    fbref_id:         Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    api_football_id:  Mapped[Optional[int]] = mapped_column(Integer,     nullable=True)
    wikidata_id:      Mapped[Optional[str]] = mapped_column(String(30),  nullable=True)
    extra:            Mapped[Optional[dict]]= mapped_column(JSONB,       nullable=True)
    nationality:   Mapped[Optional["Country"]]      = relationship(back_populates="players")
    contracts:     Mapped[list["PlayerContract"]]   = relationship(back_populates="player")
    market_values: Mapped[list["MarketValue"]]      = relationship(back_populates="player")
    transfers:     Mapped[list["Transfer"]]         = relationship(back_populates="player")
    match_stats:   Mapped[list["PlayerMatchStats"]] = relationship(back_populates="player")
    match_events:  Mapped[list["MatchEvent"]]       = relationship(
        back_populates="player",
        foreign_keys="MatchEvent.player_id",
    )

class Coach(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "coaches"
    name:            Mapped[str]           = mapped_column(String(200), nullable=False)
    date_of_birth:   Mapped[Optional[date]]= mapped_column(Date, nullable=True)
    nationality_id:  Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("countries.id"), nullable=True)
    photo_url:       Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active:       Mapped[bool]          = mapped_column(Boolean, nullable=False, default=True)
    sofascore_id:    Mapped[Optional[int]] = mapped_column(Integer, nullable=True, unique=True, index=True)
    transfermarkt_id:Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    nationality:  Mapped[Optional["Country"]] = relationship()
    team_seasons: Mapped[list["TeamSeason"]]  = relationship(back_populates="coach")

class Referee(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "referees"
    name:           Mapped[str]           = mapped_column(String(200), nullable=False)
    date_of_birth:  Mapped[Optional[date]]= mapped_column(Date, nullable=True)
    nationality_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("countries.id"), nullable=True)
    is_active:      Mapped[bool]          = mapped_column(Boolean, nullable=False, default=True)
    sofascore_id:   Mapped[Optional[int]] = mapped_column(Integer, nullable=True, unique=True, index=True)
    nationality: Mapped[Optional["Country"]] = relationship()
    matches:     Mapped[list["Match"]]       = relationship(back_populates="referee")
