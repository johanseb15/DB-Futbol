"""
Match models: fixtures, events, team stats, player match stats.
The most granular and valuable data layer.
"""
import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import (
    String,
    Integer,
    Float,
    ForeignKey,
    Boolean,
    DateTime,
    SmallInteger,
    Text,
    Index,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin


class Match(Base, UUIDMixin, TimestampMixin):
    """
    A football match.
    Core fact table — all stats and events link here.
    """
    __tablename__ = "matches"

    STATUS = ("scheduled", "live", "finished", "postponed", "cancelled", "suspended")

    # Competition context
    season_id:      Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("seasons.id"), nullable=False, index=True)
    round:          Mapped[Optional[str]]   = mapped_column(String(50), nullable=True)   # "Matchday 12", "Final"
    round_number:   Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)

    # Teams
    home_team_id:   Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False, index=True)
    away_team_id:   Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False, index=True)

    # Venue & referee
    venue_id:       Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("venues.id"), nullable=True)
    referee_id:     Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("referees.id"), nullable=True)

    # Schedule
    kickoff_time:   Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    status:         Mapped[str]             = mapped_column(String(20), nullable=False, default="scheduled")

    # Scores
    home_score:     Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    away_score:     Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    home_score_ht:  Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)  # halftime
    away_score_ht:  Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    home_score_et:  Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)  # extra time
    away_score_et:  Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    home_score_pen: Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)  # penalties
    away_score_pen: Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)

    # Attendance
    attendance:     Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)

    # External IDs
    sofascore_id:   Mapped[Optional[int]]   = mapped_column(Integer, nullable=True, unique=True, index=True)
    api_football_id:Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)

    # Raw data bucket — store full API/scrape response for reprocessing
    raw_data:       Mapped[Optional[dict]]  = mapped_column(JSONB, nullable=True)

    # Relationships
    season:          Mapped["Season"]             = relationship(back_populates="matches")
    home_team:       Mapped["Team"]               = relationship(foreign_keys=[home_team_id], back_populates="home_matches")
    away_team:       Mapped["Team"]               = relationship(foreign_keys=[away_team_id], back_populates="away_matches")
    venue:           Mapped[Optional["Venue"]]    = relationship(back_populates="matches")
    referee:         Mapped[Optional["Referee"]]  = relationship(back_populates="matches")
    events:          Mapped[list["MatchEvent"]]   = relationship(back_populates="match", order_by="MatchEvent.minute")
    team_stats:      Mapped[list["MatchTeamStats"]] = relationship(back_populates="match")
    player_stats:    Mapped[list["PlayerMatchStats"]] = relationship(back_populates="match")
    lineups:         Mapped[list["MatchLineup"]]  = relationship(back_populates="match")

    __table_args__ = (
        Index("ix_matches_kickoff_status", "kickoff_time", "status"),
        CheckConstraint(
            "status IN ('scheduled','live','finished','postponed','cancelled','suspended')",
            name="ck_matches_status_valid",
        ),
        CheckConstraint("home_score IS NULL OR home_score >= 0", name="ck_matches_home_score_nonneg"),
        CheckConstraint("away_score IS NULL OR away_score >= 0", name="ck_matches_away_score_nonneg"),
        CheckConstraint("home_score_ht IS NULL OR home_score_ht >= 0", name="ck_matches_home_ht_nonneg"),
        CheckConstraint("away_score_ht IS NULL OR away_score_ht >= 0", name="ck_matches_away_ht_nonneg"),
        CheckConstraint("home_score_et IS NULL OR home_score_et >= 0", name="ck_matches_home_et_nonneg"),
        CheckConstraint("away_score_et IS NULL OR away_score_et >= 0", name="ck_matches_away_et_nonneg"),
        CheckConstraint("home_score_pen IS NULL OR home_score_pen >= 0", name="ck_matches_home_pen_nonneg"),
        CheckConstraint("away_score_pen IS NULL OR away_score_pen >= 0", name="ck_matches_away_pen_nonneg"),
    )

    def __repr__(self) -> str:
        return f"<Match {self.home_team_id} vs {self.away_team_id} [{self.status}]>"


class MatchEvent(Base, UUIDMixin, TimestampMixin):
    """
    Individual event within a match.
    Goals, cards, substitutions, VAR decisions, penalties.
    Each event is granular and queryable.
    """
    __tablename__ = "match_events"

    TYPES = ("goal", "own_goal", "penalty_goal", "penalty_missed",
             "yellow_card", "red_card", "yellow_red_card",
             "substitution_in", "substitution_out",
             "var_decision", "injury", "other")

    match_id:     Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False, index=True)
    team_id:      Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    player_id:    Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id"), nullable=True)
    player2_id:   Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id"), nullable=True)  # assist / sub partner

    type:         Mapped[str]             = mapped_column(String(30), nullable=False, index=True)
    minute:       Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    added_time:   Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)  # "+3"
    period:       Mapped[Optional[str]]   = mapped_column(String(10), nullable=True)    # "1H", "2H", "ET1", "ET2"
    description:  Mapped[Optional[str]]   = mapped_column(String(500), nullable=True)

    # For goals: shot detail
    is_header:    Mapped[Optional[bool]]  = mapped_column(Boolean, nullable=True)
    is_freekick:  Mapped[Optional[bool]]  = mapped_column(Boolean, nullable=True)
    body_part:    Mapped[Optional[str]]   = mapped_column(String(20), nullable=True)    # "right_foot", "left_foot", "head"

    sofascore_id: Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)

    # Relationships
    match:   Mapped["Match"]            = relationship(back_populates="events")
    team:    Mapped[Optional["Team"]]   = relationship()
    player:  Mapped[Optional["Player"]] = relationship(foreign_keys=[player_id], back_populates="match_events")
    player2: Mapped[Optional["Player"]] = relationship(foreign_keys=[player2_id])

    def __repr__(self) -> str:
        return f"<MatchEvent {self.type} min={self.minute}>"


class MatchTeamStats(Base, UUIDMixin, TimestampMixin):
    """
    Aggregate team statistics for one match.
    One row per team per match (2 rows per match).
    """
    __tablename__ = "match_team_stats"

    match_id:       Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False, index=True)
    team_id:        Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"),   nullable=False)
    is_home:        Mapped[bool]      = mapped_column(Boolean, nullable=False)

    # Possession & passing
    possession:          Mapped[Optional[float]] = mapped_column(Float, nullable=True)    # 0-100
    passes:              Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    passes_accurate:     Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    pass_accuracy:       Mapped[Optional[float]] = mapped_column(Float, nullable=True)    # 0-100

    # Shots
    shots:               Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    shots_on_target:     Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    shots_off_target:    Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    shots_blocked:       Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    xg:                  Mapped[Optional[float]] = mapped_column(Float, nullable=True)    # expected goals

    # Duels & physical
    corners:             Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    fouls:               Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    offsides:            Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)

    # Discipline
    yellow_cards:        Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    red_cards:           Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)

    # Advanced (from Sofascore/FBref)
    big_chances:         Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    big_chances_missed:  Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    counter_attacks:     Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    tackles:             Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    clearances:          Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)
    interceptions:       Mapped[Optional[int]]   = mapped_column(Integer, nullable=True)

    # Relationships
    match: Mapped["Match"] = relationship(back_populates="team_stats")
    team:  Mapped["Team"]  = relationship()

    def __repr__(self) -> str:
        return f"<MatchTeamStats match={self.match_id} team={self.team_id}>"


class PlayerMatchStats(Base, UUIDMixin, TimestampMixin):
    """
    Individual player performance in a single match.
    The most granular — and most valuable — data unit.
    One row per player per match.
    """
    __tablename__ = "player_match_stats"

    match_id:        Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matches.id"),   nullable=False, index=True)
    player_id:       Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("players.id"),  nullable=False, index=True)
    team_id:         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"),    nullable=False)
    is_starter:      Mapped[bool]      = mapped_column(Boolean, nullable=False, default=False)
    jersey_number:   Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    # Time
    minutes_played:  Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    sub_in_minute:   Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    sub_out_minute:  Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    # Output
    goals:           Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    assists:         Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    own_goals:       Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)

    # Shooting
    shots:           Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    shots_on_target: Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    xg:              Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    xg_assist:       Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Passing
    passes:          Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    passes_accurate: Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    key_passes:      Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    crosses:         Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)

    # Duels
    duels_won:       Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    duels_total:     Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    dribbles_won:    Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    dribbles_total:  Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    aerial_won:      Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    aerial_total:    Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)

    # Defensive
    tackles:         Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    interceptions:   Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    clearances:      Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    blocks:          Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    fouls_committed: Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    fouls_drawn:     Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)

    # Discipline
    yellow_cards:    Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    red_cards:       Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)

    # Rating (Sofascore 1-10)
    rating:          Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # GK specific
    saves:           Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    goals_conceded:  Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    clean_sheet:     Mapped[Optional[bool]]  = mapped_column(Boolean, nullable=True)

    # Raw data (store full sofascore player stats object)
    raw_data:        Mapped[Optional[dict]]  = mapped_column(JSONB, nullable=True)

    # Relationships
    match:  Mapped["Match"]  = relationship(back_populates="player_stats")
    player: Mapped["Player"] = relationship(back_populates="match_stats")
    team:   Mapped["Team"]   = relationship()

    __table_args__ = (
        Index("ix_player_match_unique", "player_id", "match_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<PlayerMatchStats player={self.player_id} match={self.match_id}>"


class MatchLineup(Base, UUIDMixin, TimestampMixin):
    """
    Pre-match lineup / formation.
    Starting XI + bench per team.
    """
    __tablename__ = "match_lineups"

    match_id:      Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("matches.id"),  nullable=False, index=True)
    team_id:       Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"),    nullable=False)
    player_id:     Mapped[uuid.UUID]       = mapped_column(UUID(as_uuid=True), ForeignKey("players.id"),  nullable=False)
    jersey_number: Mapped[Optional[int]]   = mapped_column(SmallInteger, nullable=True)
    position_on_pitch: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)   # "GK", "CB", "ST"
    formation_place:   Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True) # 1-11
    is_starter:    Mapped[bool]            = mapped_column(Boolean, nullable=False, default=False)
    formation:     Mapped[Optional[str]]   = mapped_column(String(20), nullable=True)     # "4-3-3"

    # Relationships
    match:  Mapped["Match"]  = relationship(back_populates="lineups")
    team:   Mapped["Team"]   = relationship()
    player: Mapped["Player"] = relationship()
