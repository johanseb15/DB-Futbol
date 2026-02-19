"""
Transfer market models: player valuations and transfer history.
High business value — used for scouting, investment analysis, media.
"""
import uuid
from typing import Optional
from datetime import date

from sqlalchemy import String, Integer, BigInteger, ForeignKey, Date, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin


class MarketValue(Base, UUIDMixin, TimestampMixin):
    """
    Historical market value of a player.
    Scraped from Transfermarkt — updated whenever we run the scraper.
    
    Business use:
    - Track value trends over time
    - Identify undervalued players (value vs. performance)
    - Investment signals for player rights funds
    """
    __tablename__ = "market_values"

    player_id:   Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), ForeignKey("players.id"), nullable=False, index=True)
    team_id:     Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)

    value_eur:   Mapped[Optional[int]]  = mapped_column(BigInteger, nullable=True)   # value in euros
    recorded_at: Mapped[date]           = mapped_column(Date, nullable=False)
    source:      Mapped[str]            = mapped_column(String(50), nullable=False, default="transfermarkt")

    # Age at recording (useful for analysis)
    player_age:  Mapped[Optional[int]]  = mapped_column(Integer, nullable=True)

    # Relationships
    player: Mapped["Player"] = relationship(back_populates="market_values")
    team:   Mapped[Optional["Team"]] = relationship()

    __table_args__ = (
        Index("ix_market_values_player_date", "player_id", "recorded_at"),
    )

    def __repr__(self) -> str:
        return f"<MarketValue player={self.player_id} EUR={self.value_eur:,} @ {self.recorded_at}>"


class Transfer(Base, UUIDMixin, TimestampMixin):
    """
    A player transfer between clubs.
    Includes loans, free transfers, youth promotions.
    
    Business use:
    - Market intelligence for clubs/agents
    - Identify transfer patterns by league/country
    - Fee prediction models
    """
    __tablename__ = "transfers"

    TYPES = (
        "permanent",     # standard transfer
        "loan",          # temporary loan
        "loan_return",   # return from loan
        "free",          # free transfer (contract expiry)
        "youth",         # promotion from youth academy
        "retirement",    # player retired
        "unknown",
    )

    player_id:      Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("players.id"), nullable=False, index=True)
    from_team_id:   Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    to_team_id:     Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)

    transfer_date:  Mapped[Optional[date]]  = mapped_column(Date, nullable=True, index=True)
    season:         Mapped[Optional[str]]   = mapped_column(String(20), nullable=True)  # "2023/24"

    type:           Mapped[str]             = mapped_column(String(20), nullable=False, default="permanent")
    fee_eur:        Mapped[Optional[int]]   = mapped_column(BigInteger, nullable=True)  # null = undisclosed
    fee_undisclosed:Mapped[Optional[bool]]  = mapped_column(nullable=True)
    fee_free:       Mapped[Optional[bool]]  = mapped_column(nullable=True)              # free transfer flag

    # Loan specifics
    loan_end_date:  Mapped[Optional[date]]  = mapped_column(Date, nullable=True)
    loan_buy_option:Mapped[Optional[int]]   = mapped_column(BigInteger, nullable=True)  # purchase option fee

    # Player's market value at transfer time (from Transfermarkt)
    market_value_at_transfer: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    source:         Mapped[str]             = mapped_column(String(50), nullable=False, default="transfermarkt")
    transfermarkt_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relationships
    player:    Mapped["Player"]          = relationship(back_populates="transfers")
    from_team: Mapped[Optional["Team"]]  = relationship(foreign_keys=[from_team_id], back_populates="transfers_out")
    to_team:   Mapped[Optional["Team"]]  = relationship(foreign_keys=[to_team_id],   back_populates="transfers_in")

    def __repr__(self) -> str:
        fee = f"EUR {self.fee_eur:,}" if self.fee_eur else "undisclosed"
        return f"<Transfer {self.player_id} → {self.to_team_id} [{fee}]>"
