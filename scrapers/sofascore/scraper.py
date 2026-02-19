"""
Sofascore scraper.

Uses Sofascore's unofficial but public JSON API.
No auth required — standard browser headers are sufficient.

Covers:
- Competition seasons and rounds
- Match fixtures and results
- Match statistics (team + player level)
- Player ratings and detailed stats
- Lineups and formations
- Match events (goals, cards, subs)

Key IDs (Sofascore internal):
  Argentina Liga Profesional : competition_id = 155
  Argentina Copa Argentina   : competition_id = 329
  Premier League (ENG)       : competition_id = 17
  La Liga (ESP)              : competition_id = 8
  Serie A (ITA)              : competition_id = 23
  Bundesliga (GER)           : competition_id = 35
  Ligue 1 (FRA)              : competition_id = 34
  UEFA Champions League      : competition_id = 7
"""
import asyncio
from typing import Any, Optional

from loguru import logger

from scrapers.base import BaseScraper


# ── Competition catalog ────────────────────────────────────────────────────────
COMPETITIONS = {
    # Argentina
    "arg_liga_profesional": {"id": 155, "country": "AR", "name": "Liga Profesional", "level": 1},
    "arg_primera_nacional": {"id": 703, "country": "AR", "name": "Primera Nacional", "level": 2},
    "arg_copa_argentina":   {"id": 329, "country": "AR", "name": "Copa Argentina",   "level": 1, "type": "cup"},
    "arg_supercopa":        {"id": 706, "country": "AR", "name": "Supercopa Argentina","level": 1, "type": "cup"},

    # Europe — Top 5
    "eng_premier_league":   {"id": 17,  "country": "GB", "name": "Premier League",   "level": 1},
    "esp_la_liga":          {"id": 8,   "country": "ES", "name": "La Liga",          "level": 1},
    "ita_serie_a":          {"id": 23,  "country": "IT", "name": "Serie A",          "level": 1},
    "ger_bundesliga":       {"id": 35,  "country": "DE", "name": "Bundesliga",       "level": 1},
    "fra_ligue_1":          {"id": 34,  "country": "FR", "name": "Ligue 1",          "level": 1},

    # International club
    "ucl":                  {"id": 7,   "country": None, "name": "Champions League", "level": 1, "type": "international"},
}


class SofascoreScraper(BaseScraper):
    """
    Scraper for Sofascore's unofficial JSON API.

    API base: https://api.sofascore.com/api/v1/
    All responses are JSON — no HTML parsing needed.
    """

    SOURCE_NAME = "sofascore"
    BASE_URL    = "https://api.sofascore.com/api/v1"

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.sofascore.com/",
        "Cache-Control": "no-cache",
    }

    # ── Season ──────────────────────────────────────────────────────────────

    async def get_seasons(self, competition_id: int) -> list[dict]:
        """Fetch all seasons for a competition."""
        url = f"{self.BASE_URL}/unique-tournament/{competition_id}/seasons"
        try:
            data = await self._get(url, cache_ttl=86400)  # cache 24h
            return data.get("seasons", [])
        except Exception as e:
            self.log(f"Error fetching seasons for competition {competition_id}: {e}", "error")
            return []

    # ── Standings ───────────────────────────────────────────────────────────

    async def get_standings(self, competition_id: int, season_id: int) -> list[dict]:
        """Fetch league table for a season."""
        url = f"{self.BASE_URL}/unique-tournament/{competition_id}/season/{season_id}/standings/total"
        try:
            data = await self._get(url, cache_ttl=3600)
            standings = data.get("standings", [])
            if standings:
                return standings[0].get("rows", [])
            return []
        except Exception as e:
            self.log(f"Error fetching standings: {e}", "error")
            return []

    # ── Matches ─────────────────────────────────────────────────────────────

    async def get_rounds(self, competition_id: int, season_id: int) -> list[dict]:
        """Fetch all rounds / matchdays for a season."""
        url = f"{self.BASE_URL}/unique-tournament/{competition_id}/season/{season_id}/rounds"
        try:
            data = await self._get(url, cache_ttl=86400)
            return data.get("rounds", [])
        except Exception as e:
            self.log(f"Error fetching rounds: {e}", "error")
            return []

    async def get_matches_by_round(
        self, competition_id: int, season_id: int, round_number: int
    ) -> list[dict]:
        """Fetch all matches in a specific round."""
        url = f"{self.BASE_URL}/unique-tournament/{competition_id}/season/{season_id}/events/round/{round_number}"
        try:
            data = await self._get(url, cache_ttl=1800)
            return data.get("events", [])
        except Exception as e:
            self.log(f"Error fetching matches round {round_number}: {e}", "error")
            return []

    async def get_match(self, event_id: int) -> Optional[dict]:
        """Fetch full detail of a single match."""
        url = f"{self.BASE_URL}/event/{event_id}"
        try:
            data = await self._get(url, cache_ttl=300)
            return data.get("event")
        except Exception as e:
            self.log(f"Error fetching match {event_id}: {e}", "error")
            return None

    async def get_match_statistics(self, event_id: int) -> Optional[dict]:
        """Fetch team statistics for a match."""
        url = f"{self.BASE_URL}/event/{event_id}/statistics"
        try:
            return await self._get(url, cache_ttl=300)
        except Exception as e:
            self.log(f"Error fetching match stats {event_id}: {e}", "error")
            return None

    async def get_match_lineups(self, event_id: int) -> Optional[dict]:
        """Fetch lineups and formations for a match."""
        url = f"{self.BASE_URL}/event/{event_id}/lineups"
        try:
            return await self._get(url, cache_ttl=300)
        except Exception as e:
            self.log(f"Error fetching lineups {event_id}: {e}", "error")
            return None

    async def get_match_events(self, event_id: int) -> list[dict]:
        """Fetch match events (goals, cards, subs)."""
        url = f"{self.BASE_URL}/event/{event_id}/incidents"
        try:
            data = await self._get(url, cache_ttl=300)
            return data.get("incidents", [])
        except Exception as e:
            self.log(f"Error fetching match events {event_id}: {e}", "error")
            return []

    async def get_player_match_stats(self, event_id: int) -> Optional[dict]:
        """Fetch individual player stats for a match."""
        url = f"{self.BASE_URL}/event/{event_id}/player-statistics"
        try:
            return await self._get(url, cache_ttl=300)
        except Exception as e:
            self.log(f"Error fetching player stats {event_id}: {e}", "error")
            return None

    # ── Teams ───────────────────────────────────────────────────────────────

    async def get_team(self, team_id: int) -> Optional[dict]:
        """Fetch team profile."""
        url = f"{self.BASE_URL}/team/{team_id}"
        try:
            data = await self._get(url, cache_ttl=86400)
            return data.get("team")
        except Exception as e:
            self.log(f"Error fetching team {team_id}: {e}", "error")
            return None

    async def get_team_players(self, team_id: int) -> list[dict]:
        """Fetch current squad of a team."""
        url = f"{self.BASE_URL}/team/{team_id}/players"
        try:
            data = await self._get(url, cache_ttl=3600)
            return data.get("players", [])
        except Exception as e:
            self.log(f"Error fetching team players {team_id}: {e}", "error")
            return []

    async def get_team_matches(self, team_id: int, page: int = 0, next: bool = False) -> list[dict]:
        """Fetch recent or upcoming matches for a team."""
        direction = "next" if next else "last"
        url = f"{self.BASE_URL}/team/{team_id}/events/{direction}/{page}"
        try:
            data = await self._get(url, cache_ttl=1800)
            return data.get("events", [])
        except Exception as e:
            self.log(f"Error fetching team matches {team_id}: {e}", "error")
            return []

    # ── Players ─────────────────────────────────────────────────────────────

    async def get_player(self, player_id: int) -> Optional[dict]:
        """Fetch player profile."""
        url = f"{self.BASE_URL}/player/{player_id}"
        try:
            data = await self._get(url, cache_ttl=86400)
            return data.get("player")
        except Exception as e:
            self.log(f"Error fetching player {player_id}: {e}", "error")
            return None

    async def get_player_season_stats(
        self, player_id: int, competition_id: int, season_id: int
    ) -> Optional[dict]:
        """Fetch a player's aggregated stats for a full season."""
        url = f"{self.BASE_URL}/player/{player_id}/unique-tournament/{competition_id}/season/{season_id}/statistics/overall"
        try:
            return await self._get(url, cache_ttl=3600)
        except Exception as e:
            self.log(f"Error fetching player season stats {player_id}: {e}", "error")
            return None

    async def get_player_transfer_history(self, player_id: int) -> list[dict]:
        """Fetch transfer history for a player."""
        url = f"{self.BASE_URL}/player/{player_id}/transfer-history"
        try:
            data = await self._get(url, cache_ttl=86400)
            return data.get("transferHistory", [])
        except Exception as e:
            self.log(f"Error fetching transfer history {player_id}: {e}", "error")
            return []

    # ── Main scrape entrypoint ───────────────────────────────────────────────

    async def scrape(self, competition_key: str, season_id: int) -> dict:
        """
        Full scrape for a competition season.
        Returns raw collected data — normalization happens separately.
        """
        comp = COMPETITIONS.get(competition_key)
        if not comp:
            raise ValueError(f"Unknown competition key: {competition_key}")

        competition_id = comp["id"]
        self.log(f"Starting scrape: {comp['name']} season {season_id}")

        result = {
            "competition": comp,
            "season_id": season_id,
            "matches": [],
            "teams": {},
            "players": {},
        }

        # 1. Get all rounds
        rounds = await self.get_rounds(competition_id, season_id)
        self.log(f"Found {len(rounds)} rounds")

        # 2. For each round, get matches
        for round_info in rounds:
            round_number = round_info.get("round")
            if round_number is None:
                continue

            matches = await self.get_matches_by_round(competition_id, season_id, round_number)
            self.log(f"Round {round_number}: {len(matches)} matches")

            for match in matches:
                event_id = match.get("id")
                if not event_id:
                    continue

                # 3. Per match: get stats, lineups, events
                match_data = {
                    "match":      match,
                    "statistics": await self.get_match_statistics(event_id),
                    "lineups":    await self.get_match_lineups(event_id),
                    "incidents":  await self.get_match_events(event_id),
                    "player_stats": await self.get_player_match_stats(event_id),
                }
                result["matches"].append(match_data)

        self.log(f"Scrape complete: {len(result['matches'])} matches collected")
        return result
