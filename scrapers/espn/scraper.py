"""
ESPN fallback scraper for match lists.

Uses ESPN public scoreboard endpoints (no paid API key):
  https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from scrapers.base import BaseScraper


LEAGUE_MAP = {
    "arg_liga_profesional": "arg.1",
    "eng_premier_league": "eng.1",
    "esp_la_liga": "esp.1",
    "ita_serie_a": "ita.1",
    "ger_bundesliga": "ger.1",
    "fra_ligue_1": "fra.1",
    "ucl": "uefa.champions",
}


class ESPNFallbackScraper(BaseScraper):
    SOURCE_NAME = "espn_fallback"
    BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer"

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.espn.com/",
    }

    async def scrape(self, competition_key: str, season_id: int) -> dict:
        league_code = LEAGUE_MAP.get(competition_key)
        if not league_code:
            self.log(f"No ESPN mapping for competition '{competition_key}'.", "warning")
            return self._empty_result(competition_key, season_id)

        events = await self._collect_events_window(league_code, days_back=21, days_forward=21)
        matches = [self._to_sofascore_like_match(e, season_id) for e in events]
        matches = [m for m in matches if m is not None]

        self.log(f"Fallback collected {len(matches)} matches from ESPN for {competition_key}.")
        return {
            "competition": {"id": league_code, "name": competition_key, "source": "espn"},
            "season_id": season_id,
            "matches": matches,
            "teams": {},
            "players": {},
            "fallback_source": "espn",
        }

    async def discover_seasons(self, competition_key: str, years_back: int = 5) -> list[dict]:
        """
        Fallback season discovery.
        ESPN doesn't expose Sofascore season IDs, so we infer season years from events.
        """
        league_code = LEAGUE_MAP.get(competition_key)
        if not league_code:
            return []

        years = set()
        current_year = datetime.now(timezone.utc).year
        for year in range(current_year - years_back, current_year + 2):
            start = f"{year}0101"
            end = f"{year}1231"
            date_range = f"{start}-{end}"
            url = f"{self.BASE_URL}/{league_code}/scoreboard"
            try:
                payload = await self._get(url, params={"dates": date_range}, cache_ttl=1800)
            except Exception:
                continue
            events = payload.get("events", []) if isinstance(payload, dict) else []
            if events:
                years.add(year)

        result = [{"id": y, "year": str(y), "source": "espn"} for y in sorted(years, reverse=True)]
        return result

    async def _collect_events_window(self, league_code: str, days_back: int, days_forward: int) -> list[dict]:
        today = datetime.now(timezone.utc).date()
        ranges = [
            (
                (today - timedelta(days=days_back)).strftime("%Y%m%d"),
                today.strftime("%Y%m%d"),
            ),
            (
                today.strftime("%Y%m%d"),
                (today + timedelta(days=days_forward)).strftime("%Y%m%d"),
            ),
        ]

        all_events: dict[str, dict] = {}
        url = f"{self.BASE_URL}/{league_code}/scoreboard"

        for start, end in ranges:
            date_range = f"{start}-{end}"
            try:
                payload = await self._get(url, params={"dates": date_range}, cache_ttl=900)
            except Exception as e:
                self.log(f"ESPN fetch failed for {league_code} in range {date_range}: {e}", "warning")
                continue

            events = payload.get("events", []) if isinstance(payload, dict) else []
            for event in events:
                ev_id = str(event.get("id", ""))
                if ev_id:
                    all_events[ev_id] = event

        return list(all_events.values())

    def _to_sofascore_like_match(self, event: dict, season_id: int) -> Optional[dict]:
        try:
            comp = (event.get("competitions") or [{}])[0]
            competitors = comp.get("competitors") or []
            home = next((x for x in competitors if x.get("homeAway") == "home"), None)
            away = next((x for x in competitors if x.get("homeAway") == "away"), None)
            if not home or not away:
                return None

            kickoff = event.get("date")
            kickoff_ts = None
            if kickoff:
                kickoff_ts = int(datetime.fromisoformat(kickoff.replace("Z", "+00:00")).timestamp())

            espn_state = ((comp.get("status") or {}).get("type") or {}).get("state", "").lower()
            state_map = {"pre": "notstarted", "in": "inprogress", "post": "finished"}
            status_type = state_map.get(espn_state, "notstarted")

            home_team = home.get("team", {})
            away_team = away.get("team", {})
            league = ((event.get("leagues") or [{}])[0]).get("name")
            round_name = ((comp.get("status") or {}).get("type") or {}).get("detail")

            match_stub = {
                "id": int(event.get("id")) if str(event.get("id", "")).isdigit() else None,
                "startTimestamp": kickoff_ts,
                "homeTeam": {
                    "id": int(home_team.get("id")) if str(home_team.get("id", "")).isdigit() else None,
                    "name": home_team.get("displayName"),
                    "shortName": home_team.get("shortDisplayName"),
                },
                "awayTeam": {
                    "id": int(away_team.get("id")) if str(away_team.get("id", "")).isdigit() else None,
                    "name": away_team.get("displayName"),
                    "shortName": away_team.get("shortDisplayName"),
                },
                "homeScore": {"current": _safe_int(home.get("score"))},
                "awayScore": {"current": _safe_int(away.get("score"))},
                "status": {"type": status_type},
                "roundInfo": {"name": round_name, "round": None},
                "tournament": {
                    "uniqueTournament": {"id": None, "name": league or "Unknown"},
                    "name": league or "Unknown",
                },
                "season": {"id": season_id, "year": str(season_id)},
            }

            if not match_stub["id"] or not match_stub["homeTeam"]["name"] or not match_stub["awayTeam"]["name"]:
                return None

            return {
                "match": match_stub,
                "statistics": None,
                "lineups": None,
                "incidents": [],
                "player_stats": None,
            }
        except Exception:
            return None

    def _empty_result(self, competition_key: str, season_id: int) -> dict:
        return {
            "competition": {"id": None, "name": competition_key, "source": "espn"},
            "season_id": season_id,
            "matches": [],
            "teams": {},
            "players": {},
            "fallback_source": "espn",
        }


def _safe_int(v):
    try:
        return int(v)
    except Exception:
        return None
