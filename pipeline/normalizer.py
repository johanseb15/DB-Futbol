"""
Normalization pipeline.

Takes raw data from scrapers and writes clean, normalized records
into the PostgreSQL database.

Design principles:
- Idempotent: running twice doesn't create duplicates (upsert pattern)
- Source-of-truth IDs: always use sofascore_id / transfermarkt_id to dedup
- Fail gracefully: log + skip bad records, never abort full pipeline
- Store raw: always write raw payload to scrape_raw before normalizing
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    Country, Competition, Season, Venue, Team, Player, Coach, Referee,
    Match, MatchEvent, MatchTeamStats, PlayerMatchStats, MatchLineup,
    MarketValue, Transfer, PlayerContract,
)


class SofascoreNormalizer:
    """
    Transforms Sofascore raw data into clean DB records.
    All methods are async and work within a single session.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._country_cache: dict[str, uuid.UUID] = {}
        self._team_cache:    dict[int, uuid.UUID]  = {}
        self._player_cache:  dict[int, uuid.UUID]  = {}
        self._venue_cache:   dict[int, uuid.UUID]  = {}

    # ── Entry point ──────────────────────────────────────────────────────────

    async def normalize_full_scrape(self, raw: dict) -> dict:
        """
        Process a full competition season scrape from SofascoreScraper.scrape().
        Returns summary of records created/updated.
        """
        stats = {"matches": 0, "events": 0, "team_stats": 0, "player_stats": 0, "errors": 0}

        for match_data in raw.get("matches", []):
            try:
                await self.normalize_match(match_data)
                stats["matches"] += 1
            except Exception as e:
                logger.error(f"Error normalizing match: {e}")
                stats["errors"] += 1

        await self.session.flush()
        return stats

    # ── Match ─────────────────────────────────────────────────────────────────

    async def normalize_match(self, match_data: dict) -> Optional[uuid.UUID]:
        """
        Normalize a single match and all its sub-data.
        Returns the match UUID.
        """
        event = match_data.get("match", {})
        if not event:
            return None

        match_id = await self._upsert_match(event)
        if not match_id:
            return None

        # Events (goals, cards, subs)
        incidents = match_data.get("incidents", [])
        if incidents:
            await self._normalize_incidents(match_id, event, incidents)

        # Team stats
        statistics = match_data.get("statistics")
        if statistics:
            home_id = await self._get_team_id(event.get("homeTeam", {}).get("id"))
            away_id = await self._get_team_id(event.get("awayTeam", {}).get("id"))
            if home_id and away_id:
                await self._normalize_team_stats(match_id, home_id, away_id, statistics)

        # Player stats
        player_stats = match_data.get("player_stats")
        if player_stats:
            await self._normalize_player_stats(match_id, event, player_stats)

        return match_id

    async def _upsert_match(self, event: dict) -> Optional[uuid.UUID]:
        """Insert or update a match record."""
        sofascore_id = event.get("id")
        if not sofascore_id:
            return None

        home_team_ss = event.get("homeTeam", {})
        away_team_ss = event.get("awayTeam", {})

        home_team_id = await self._get_or_create_team(home_team_ss)
        away_team_id = await self._get_or_create_team(away_team_ss)

        if not home_team_id or not away_team_id:
            return None

        # Parse status
        status_map = {
            "notstarted": "scheduled",
            "inprogress": "live",
            "finished":   "finished",
            "postponed":  "postponed",
            "canceled":   "cancelled",
        }
        ss_status  = event.get("status", {})
        status_type = ss_status.get("type", "notstarted")
        status = status_map.get(status_type, "scheduled")

        # Parse kickoff time
        kickoff = None
        ts = event.get("startTimestamp")
        if ts:
            kickoff = datetime.fromtimestamp(ts, tz=timezone.utc)

        # Scores
        home_score = event.get("homeScore", {}).get("current")
        away_score = event.get("awayScore", {}).get("current")
        home_ht    = event.get("homeScore", {}).get("period1")
        away_ht    = event.get("awayScore", {}).get("period1")

        # Check if exists
        result = await self.session.execute(
            select(Match).where(Match.sofascore_id == sofascore_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.status     = status
            existing.home_score = home_score
            existing.away_score = away_score
            existing.home_score_ht = home_ht
            existing.away_score_ht = away_ht
            existing.raw_data   = event
            return existing.id
        else:
            # We need a season_id — use a placeholder if not resolved
            season_id = await self._resolve_season(event)

            new_match = Match(
                season_id    = season_id,
                home_team_id = home_team_id,
                away_team_id = away_team_id,
                status       = status,
                kickoff_time = kickoff,
                home_score   = home_score,
                away_score   = away_score,
                home_score_ht = home_ht,
                away_score_ht = away_ht,
                round        = str(event.get("roundInfo", {}).get("name", "")),
                round_number = event.get("roundInfo", {}).get("round"),
                sofascore_id = sofascore_id,
                raw_data     = event,
            )
            self.session.add(new_match)
            await self.session.flush()
            return new_match.id

    async def _normalize_incidents(
        self, match_id: uuid.UUID, event: dict, incidents: list[dict]
    ) -> None:
        """Normalize match events (goals, cards, subs)."""
        incident_type_map = {
            "goal":               "goal",
            "ownGoal":            "own_goal",
            "penaltyMissed":      "penalty_missed",
            "yellowCard":         "yellow_card",
            "directRedCard":      "red_card",
            "yellowRedCard":      "yellow_red_card",
            "substitution":       "substitution_in",
            "varDecision":        "var_decision",
            "injuryTime":         "other",
        }

        # Clear existing events for this match (re-scrape idempotency)
        await self.session.execute(
            MatchEvent.__table__.delete().where(MatchEvent.match_id == match_id)
        )

        home_id = await self._get_team_id(event.get("homeTeam", {}).get("id"))
        away_id = await self._get_team_id(event.get("awayTeam", {}).get("id"))

        for inc in incidents:
            inc_type = inc.get("incidentType")
            normalized_type = incident_type_map.get(inc_type, "other")

            # Determine team
            is_home = inc.get("isHome", False)
            team_id = home_id if is_home else away_id

            # Player
            player_data = inc.get("player") or {}
            player_id = await self._get_or_create_player(player_data) if player_data.get("id") else None

            # Assist / sub partner
            assist_data = inc.get("assist1") or inc.get("playerOut") or {}
            player2_id = await self._get_or_create_player(assist_data) if assist_data.get("id") else None

            new_event = MatchEvent(
                match_id    = match_id,
                team_id     = team_id,
                player_id   = player_id,
                player2_id  = player2_id,
                type        = normalized_type,
                minute      = inc.get("time"),
                added_time  = inc.get("addedTime"),
                period      = "1H" if (inc.get("time") or 0) <= 45 else "2H",
                description = inc.get("text"),
            )
            self.session.add(new_event)

    async def _normalize_team_stats(
        self, match_id: uuid.UUID, home_id: uuid.UUID, away_id: uuid.UUID, statistics: dict
    ) -> None:
        """Normalize team-level match statistics."""
        periods = statistics.get("statistics", [])
        if not periods:
            return

        # Use "ALL" period (full match), fallback to first period
        all_period = next((p for p in periods if p.get("period") == "ALL"), periods[0] if periods else None)
        if not all_period:
            return

        def extract(stat_name: str, is_home: bool) -> Any:
            for group in all_period.get("groups", []):
                for item in group.get("statisticsItems", []):
                    if item.get("key") == stat_name:
                        val = item.get("homeValue" if is_home else "awayValue")
                        try:
                            return float(val) if "." in str(val) else int(val)
                        except (TypeError, ValueError):
                            return None
            return None

        for is_home, team_id in [(True, home_id), (False, away_id)]:
            # Delete old stats if re-processing
            await self.session.execute(
                MatchTeamStats.__table__.delete().where(
                    MatchTeamStats.match_id == match_id,
                    MatchTeamStats.team_id  == team_id,
                )
            )
            stats = MatchTeamStats(
                match_id            = match_id,
                team_id             = team_id,
                is_home             = is_home,
                possession          = extract("ballPossession", is_home),
                shots               = extract("totalShots", is_home),
                shots_on_target     = extract("shotsOnTarget", is_home),
                shots_off_target    = extract("shotsOffTarget", is_home),
                shots_blocked       = extract("blockedShots", is_home),
                corners             = extract("cornerKicks", is_home),
                fouls               = extract("fouls", is_home),
                offsides            = extract("offsides", is_home),
                yellow_cards        = extract("yellowCards", is_home),
                red_cards           = extract("redCards", is_home),
                passes              = extract("totalPasses", is_home),
                passes_accurate     = extract("accuratePasses", is_home),
                xg                  = extract("expectedGoals", is_home),
                big_chances         = extract("bigChances", is_home),
                big_chances_missed  = extract("bigChancesMissed", is_home),
                tackles             = extract("tackles", is_home),
                clearances          = extract("clearances", is_home),
                interceptions       = extract("interceptions", is_home),
            )
            self.session.add(stats)

    async def _normalize_player_stats(
        self, match_id: uuid.UUID, event: dict, player_stats_raw: dict
    ) -> None:
        """Normalize per-player stats for a match."""
        home_id = await self._get_team_id(event.get("homeTeam", {}).get("id"))
        away_id = await self._get_team_id(event.get("awayTeam", {}).get("id"))

        for side, team_id in [("home", home_id), ("away", away_id)]:
            players = player_stats_raw.get(side, {}).get("players", [])
            for entry in players:
                p_data = entry.get("player", {})
                if not p_data.get("id"):
                    continue

                player_id = await self._get_or_create_player(p_data)
                if not player_id:
                    continue

                s = entry.get("statistics", {})

                # Delete old record
                await self.session.execute(
                    PlayerMatchStats.__table__.delete().where(
                        PlayerMatchStats.match_id  == match_id,
                        PlayerMatchStats.player_id == player_id,
                    )
                )

                ps = PlayerMatchStats(
                    match_id          = match_id,
                    player_id         = player_id,
                    team_id           = team_id,
                    is_starter        = s.get("started") or False,
                    minutes_played    = s.get("minutesPlayed"),
                    goals             = s.get("goals"),
                    assists           = s.get("goalAssist"),
                    shots             = s.get("totalShots"),
                    shots_on_target   = s.get("onTargetScoringAttempt"),
                    xg                = s.get("expectedGoals"),
                    passes            = s.get("totalPasses"),
                    passes_accurate   = s.get("accuratePasses"),
                    key_passes        = s.get("keyPass"),
                    duels_won         = s.get("duelWon"),
                    duels_total       = s.get("duelLost", 0) + (s.get("duelWon") or 0),
                    dribbles_won      = s.get("successfulDribble"),
                    tackles           = s.get("tackle"),
                    interceptions     = s.get("interceptionWon"),
                    fouls_committed   = s.get("fouls"),
                    yellow_cards      = s.get("yellowCard"),
                    red_cards         = s.get("redCard"),
                    rating            = s.get("rating"),
                    saves             = s.get("saves"),
                    goals_conceded    = s.get("goalsConceded"),
                    raw_data          = s,
                )
                self.session.add(ps)

    # ── Entity get-or-create helpers ─────────────────────────────────────────

    async def _get_or_create_team(self, team_data: dict) -> Optional[uuid.UUID]:
        """Get existing team or create from Sofascore team object."""
        ss_id = team_data.get("id")
        if not ss_id:
            return None

        if ss_id in self._team_cache:
            return self._team_cache[ss_id]

        result = await self.session.execute(
            select(Team).where(Team.sofascore_id == ss_id)
        )
        team = result.scalar_one_or_none()

        if not team:
            country_id = None
            country_data = team_data.get("country", {})
            if country_data.get("alpha2"):
                country_id = await self._get_or_create_country(
                    country_data["alpha2"],
                    country_data.get("name", country_data["alpha2"])
                )

            team = Team(
                name         = team_data.get("name", "Unknown"),
                short_name   = team_data.get("shortName") or team_data.get("nameCode"),
                country_id   = country_id,
                sofascore_id = ss_id,
                logo_url     = f"https://api.sofascore.com/api/v1/team/{ss_id}/image",
            )
            self.session.add(team)
            await self.session.flush()

        self._team_cache[ss_id] = team.id
        return team.id

    async def _get_or_create_player(self, player_data: dict) -> Optional[uuid.UUID]:
        """Get existing player or create from Sofascore player object."""
        ss_id = player_data.get("id")
        if not ss_id:
            return None

        if ss_id in self._player_cache:
            return self._player_cache[ss_id]

        result = await self.session.execute(
            select(Player).where(Player.sofascore_id == ss_id)
        )
        player = result.scalar_one_or_none()

        if not player:
            pos_map = {
                "G": "GK", "D": "CB", "M": "CM", "F": "ST",
            }
            position = pos_map.get(
                player_data.get("position", ""),
                player_data.get("position")
            )

            player = Player(
                name         = player_data.get("name", "Unknown"),
                sofascore_id = ss_id,
                position     = position,
                photo_url    = f"https://api.sofascore.com/api/v1/player/{ss_id}/image",
            )
            self.session.add(player)
            await self.session.flush()

        self._player_cache[ss_id] = player.id
        return player.id

    async def _get_or_create_country(self, code: str, name: str) -> Optional[uuid.UUID]:
        """Get or create country by ISO2 code."""
        code = code.upper()
        if code in self._country_cache:
            return self._country_cache[code]

        result = await self.session.execute(
            select(Country).where(Country.code_iso2 == code)
        )
        country = result.scalar_one_or_none()

        if not country:
            country = Country(name=name, code_iso2=code)
            self.session.add(country)
            await self.session.flush()

        self._country_cache[code] = country.id
        return country.id

    async def _get_team_id(self, ss_id: Optional[int]) -> Optional[uuid.UUID]:
        """Lookup team UUID from Sofascore ID."""
        if not ss_id:
            return None
        if ss_id in self._team_cache:
            return self._team_cache[ss_id]
        result = await self.session.execute(
            select(Team.id).where(Team.sofascore_id == ss_id)
        )
        row = result.scalar_one_or_none()
        if row:
            self._team_cache[ss_id] = row
        return row

    async def _resolve_season(self, event: dict) -> uuid.UUID:
        """
        Resolve or create a Season record from a Sofascore event.
        Creates Competition if needed.
        """
        tournament = event.get("tournament", {})
        unique_tournament = tournament.get("uniqueTournament", {})
        season_info = event.get("season", {})

        comp_ss_id   = unique_tournament.get("id")
        season_ss_id = season_info.get("id")
        season_name  = season_info.get("year", str(season_info.get("id", "unknown")))
        comp_name    = unique_tournament.get("name", "Unknown Competition")

        # Find or create competition
        comp = None
        if comp_ss_id:
            result = await self.session.execute(
                select(Competition).where(Competition.sofascore_id == comp_ss_id)
            )
            comp = result.scalar_one_or_none()

        if not comp:
            comp = Competition(
                name         = comp_name,
                type         = "league",
                sofascore_id = comp_ss_id,
            )
            self.session.add(comp)
            await self.session.flush()

        # Find or create season
        season = None
        if season_ss_id:
            result = await self.session.execute(
                select(Season).where(Season.sofascore_id == season_ss_id)
            )
            season = result.scalar_one_or_none()

        if not season:
            season = Season(
                competition_id = comp.id,
                name           = season_name,
                sofascore_id   = season_ss_id,
            )
            self.session.add(season)
            await self.session.flush()

        return season.id


class TransfermarktNormalizer:
    """
    Transforms Transfermarkt raw data into clean DB records.
    Works alongside SofascoreNormalizer — links players by name/ID.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def normalize_player_data(
        self, player: Player, raw: dict
    ) -> None:
        """
        Enrich an existing player record with Transfermarkt data.
        Updates market values + transfer history.
        """
        # Update player profile fields from TM
        profile = raw.get("profile", {})
        if profile:
            if profile.get("height_cm"):
                player.height_cm = profile["height_cm"]
            if profile.get("foot"):
                player.foot = profile["foot"]
            if profile.get("date_of_birth_raw"):
                player.extra = player.extra or {}
                player.extra["tm_dob_raw"] = profile["date_of_birth_raw"]

        # Market value history
        for mv_entry in raw.get("market_values", []):
            from datetime import date as date_type
            recorded = mv_entry.get("recorded_at")
            if not recorded:
                continue
            try:
                recorded_date = date_type.fromisoformat(recorded)
            except (ValueError, TypeError):
                continue

            new_mv = MarketValue(
                player_id   = player.id,
                value_eur   = mv_entry.get("value_eur"),
                recorded_at = recorded_date,
                player_age  = mv_entry.get("player_age"),
                source      = "transfermarkt",
            )
            self.session.add(new_mv)

        # Transfer history
        for t_entry in raw.get("transfers", []):
            transfer = Transfer(
                player_id        = player.id,
                fee_eur          = t_entry.get("fee_eur"),
                fee_undisclosed  = t_entry.get("is_undisclosed"),
                fee_free         = t_entry.get("is_free"),
                type             = "loan" if t_entry.get("is_loan") else "permanent",
                season           = t_entry.get("season"),
                source           = "transfermarkt",
            )
            self.session.add(transfer)

        await self.session.flush()
