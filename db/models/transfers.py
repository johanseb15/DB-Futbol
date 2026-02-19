import uuid
from typing import Optional
from datetime import date
from sqlalchemy import String, Integer, BigInteger, ForeignKey, Date, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin, UUIDMixin

class MarketValue(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "market_values"
    player_id:   Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("players.id"), nullable=False, index=True)
    team_id:     Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    value_eur:   Mapped[Optional[int]]  = mapped_column(BigInteger, nullable=True)
    recorded_at: Mapped[date]           = mapped_column(Date, nullable=False)
    source:      Mapped[str]            = mapped_column(String(50), nullable=False, default="transfermarkt")
    player_age:  Mapped[Optional[int]]  = mapped_column(Integer, nullable=True)
    player: Mapped["Player"]         = relationship(back_populates="market_values")
    team:   Mapped[Optional["Team"]] = relationship()
    __table_args__ = (Index("ix_market_values_player_date", "player_id", "recorded_at"),)

class Transfer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "transfers"
    player_id:       Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("players.id"), nullable=False, index=True)
    from_team_id:    Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    to_team_id:      Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    transfer_date:   Mapped[Optional[date]]  = mapped_column(Date, nullable=True, index=True)
    season:          Mapped[Optional[str]]   = mapped_column(String(20), nullable=True)
    type:            Mapped[str]             = mapped_column(String(20), nullable=False, default="permanent")
    fee_eur:         Mapped[Optional[int]]   = mapped_column(BigInteger, nullable=True)
    fee_undisclosed: Mapped[Optional[bool]]  = mapped_column(nullable=True)
    fee_free:        Mapped[Optional[bool]]  = mapped_column(nullable=True)
    loan_end_date:   Mapped[Optional[date]]  = mapped_column(Date, nullable=True)
    loan_buy_option: Mapped[Optional[int]]   = mapped_column(BigInteger, nullable=True)
    market_value_at_transfer: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    source:          Mapped[str]             = mapped_column(String(50), nullable=False, default="transfermarkt")
    transfermarkt_id:Mapped[Optional[str]]   = mapped_column(String(100), nullable=True)
    player:    Mapped["Player"]         = relationship(back_populates="transfers")
    from_team: Mapped[Optional["Team"]] = relationship(foreign_keys=[from_team_id], back_populates="transfers_out")
    to_team:   Mapped[Optional["Team"]] = relationship(foreign_keys=[to_team_id],   back_populates="transfers_in")
