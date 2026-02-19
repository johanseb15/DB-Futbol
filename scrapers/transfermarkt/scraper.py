"""
Transfermarkt scraper.

Transfermarkt is HTML-based — we parse the DOM.
Uses httpx for requests + selectolax for fast HTML parsing.

Covers:
- Player market values (current + historical)
- Transfer history
- Player biographical data
- Squad lists per team/season
"""
import re
from typing import Optional
from datetime import date, datetime

from selectolax.parser import HTMLParser
from loguru import logger

from scrapers.base import BaseScraper


# Transfermarkt club IDs for our scope
TEAM_IDS = {
    # Argentina — top clubs
    "river_plate":    35,
    "boca_juniors":   821,
    "racing":         3167,
    "independiente":  3168,
    "san_lorenzo":    3869,
    "talleres":       17780,
    "estudiantes":    3451,
    "huracan":        7021,
    "belgrano":       6581,
    "atletico_tucuman": 9089,

    # England
    "man_city":    281,
    "arsenal":     11,
    "liverpool":   31,
    "chelsea":     631,
    "man_utd":     985,

    # Spain
    "real_madrid": 418,
    "barcelona":   131,
    "atletico":    13,
    "sevilla":     368,
    "real_sociedad": 681,

    # Italy
    "juventus":    506,
    "inter":       46,
    "milan":       5,
    "napoli":      6195,
    "roma":        12,

    # Germany
    "Bayern":      27,
    "dortmund":    16,
    "leverkusen":  15,
    "rb_leipzig":  23826,

    # France
    "psg":         583,
    "marseille":   244,
    "monaco":      162,
    "lille":       1082,
}


class TransfermarktScraper(BaseScraper):
    """
    Scraper for transfermarkt.com

    Rate limiting is critical here — Transfermarkt blocks aggressively.
    We use a 12-second minimum delay between requests.
    """

    SOURCE_NAME = "transfermarkt"
    BASE_URL    = "https://www.transfermarkt.com"

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-AR,es;q=0.9,en-US;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.transfermarkt.com/",
    }

    # ── Player profile ───────────────────────────────────────────────────────

    async def get_player_profile(self, player_slug: str, player_id: int) -> Optional[dict]:
        """
        Scrape player profile page.
        URL pattern: /player-name/profil/spieler/{id}
        """
        url = f"{self.BASE_URL}/{player_slug}/profil/spieler/{player_id}"
        try:
            html = await self._get(url, cache_ttl=86400)
            return self._parse_player_profile(html, player_id)
        except Exception as e:
            self.log(f"Error fetching player profile {player_id}: {e}", "error")
            return None

    def _parse_player_profile(self, html: str, player_id: int) -> dict:
        """Parse player profile HTML into structured dict."""
        tree = HTMLParser(html)
        data = {"transfermarkt_id": str(player_id)}

        # Full name
        header = tree.css_first("h1.data-header__headline-wrapper")
        if header:
            data["name"] = header.text(strip=True)

        # Info table: position, foot, height, nationality, dob
        info_items = tree.css("span.info-table__content")
        labels = tree.css("span.info-table__content--bold")

        label_map = {}
        for label, value in zip(labels, info_items):
            label_map[label.text(strip=True).lower()] = value.text(strip=True)

        if "position:" in label_map:
            data["position"] = label_map["position:"]
        if "foot:" in label_map:
            data["foot"] = label_map["foot:"].lower()
        if "height:" in label_map:
            raw_h = label_map["height:"].replace(",", ".").replace("m", "").strip()
            try:
                data["height_cm"] = int(float(raw_h) * 100)
            except (ValueError, TypeError):
                pass
        if "date of birth:" in label_map:
            data["date_of_birth_raw"] = label_map["date of birth:"]
        if "nationality:" in label_map:
            data["nationality"] = label_map["nationality:"]

        # Current market value
        mv_elem = tree.css_first("a.data-header__market-value-wrapper")
        if mv_elem:
            data["market_value_raw"] = mv_elem.text(strip=True)
            data["market_value_eur"] = self._parse_value(mv_elem.text(strip=True))

        # Current club
        club_elem = tree.css_first("span.data-header__club a")
        if club_elem:
            data["current_club"] = club_elem.text(strip=True)

        return data

    # ── Market value history ─────────────────────────────────────────────────

    async def get_market_value_history(self, player_slug: str, player_id: int) -> list[dict]:
        """
        Scrape historical market values for a player.
        Transfermarkt stores these as a JS data object in the page source.
        """
        url = f"{self.BASE_URL}/{player_slug}/marktwertverlauf/spieler/{player_id}"
        try:
            html = await self._get(url, cache_ttl=86400)
            return self._parse_market_value_history(html)
        except Exception as e:
            self.log(f"Error fetching market value history {player_id}: {e}", "error")
            return []

    def _parse_market_value_history(self, html: str) -> list[dict]:
        """
        Extract market value timeline from the highcharts data embedded in the page.
        Transfermarkt embeds this as: chart.series[0].data = [...]
        """
        history = []

        # Find the highcharts series data in the page source
        pattern = r'"series":\[{"type":"line","data":\[(.+?)\]'
        match = re.search(pattern, html)
        if not match:
            return history

        # Each data point: {"y":value,"datum":"DD.MM.YYYY","verein":"Club","age":N,"mw":"€Xm"}
        point_pattern = r'\{"y":(\d+),"datum":"([^"]+)","verein":"([^"]+)","age":(\d+),"mw":"([^"]+)"'
        points = re.findall(point_pattern, match.group(1))

        for raw_value, datum, club, age, mw_text in points:
            try:
                parsed_date = datetime.strptime(datum, "%b %d, %Y").date()
            except ValueError:
                try:
                    parsed_date = datetime.strptime(datum, "%d.%m.%Y").date()
                except ValueError:
                    continue

            history.append({
                "value_eur":   int(raw_value),
                "recorded_at": parsed_date.isoformat(),
                "club":        club,
                "player_age":  int(age),
                "value_label": mw_text,
            })

        return history

    # ── Transfer history ─────────────────────────────────────────────────────

    async def get_transfer_history(self, player_slug: str, player_id: int) -> list[dict]:
        """Scrape all transfers for a player."""
        url = f"{self.BASE_URL}/{player_slug}/transfers/spieler/{player_id}"
        try:
            html = await self._get(url, cache_ttl=86400)
            return self._parse_transfers(html)
        except Exception as e:
            self.log(f"Error fetching transfer history {player_id}: {e}", "error")
            return []

    def _parse_transfers(self, html: str) -> list[dict]:
        """Parse transfers table."""
        tree = HTMLParser(html)
        transfers = []

        rows = tree.css("div.tm-player-transfer-history-grid")
        for row in rows:
            cells = row.css("div")
            if len(cells) < 5:
                continue

            transfer = {}

            # Season
            season_node = row.css_first("div.tm-player-transfer-history-grid__season")
            if season_node:
                transfer["season"] = season_node.text(strip=True)

            # Date
            date_node = row.css_first("div.tm-player-transfer-history-grid__date")
            if date_node:
                transfer["date_raw"] = date_node.text(strip=True)

            # From club
            from_node = row.css_first("div.tm-player-transfer-history-grid__old-club a")
            if from_node:
                transfer["from_club"] = from_node.text(strip=True)
                href = from_node.attributes.get("href", "")
                tm_id_match = re.search(r"/(\d+)$", href)
                if tm_id_match:
                    transfer["from_club_tm_id"] = tm_id_match.group(1)

            # To club
            to_node = row.css_first("div.tm-player-transfer-history-grid__new-club a")
            if to_node:
                transfer["to_club"] = to_node.text(strip=True)
                href = to_node.attributes.get("href", "")
                tm_id_match = re.search(r"/(\d+)$", href)
                if tm_id_match:
                    transfer["to_club_tm_id"] = tm_id_match.group(1)

            # Fee
            fee_node = row.css_first("div.tm-player-transfer-history-grid__fee")
            if fee_node:
                raw_fee = fee_node.text(strip=True)
                transfer["fee_raw"] = raw_fee
                transfer["fee_eur"] = self._parse_value(raw_fee)
                transfer["is_free"] = "free transfer" in raw_fee.lower()
                transfer["is_loan"] = "loan" in raw_fee.lower()
                transfer["is_undisclosed"] = "?" in raw_fee or "undisclosed" in raw_fee.lower()

            if transfer.get("from_club") or transfer.get("to_club"):
                transfers.append(transfer)

        return transfers

    # ── Squad ────────────────────────────────────────────────────────────────

    async def get_squad(self, club_slug: str, club_id: int, season: str = "2024") -> list[dict]:
        """
        Scrape squad roster for a club in a given season.
        Season format: "2024" (for 2024/25) or "2023" (for 2023/24)
        """
        url = f"{self.BASE_URL}/{club_slug}/kader/verein/{club_id}/saison_id/{season}"
        try:
            html = await self._get(url, cache_ttl=3600)
            return self._parse_squad(html)
        except Exception as e:
            self.log(f"Error fetching squad {club_id}: {e}", "error")
            return []

    def _parse_squad(self, html: str) -> list[dict]:
        """Parse squad table."""
        tree = HTMLParser(html)
        players = []

        rows = tree.css("table.items > tbody > tr.odd, table.items > tbody > tr.even")
        for row in rows:
            player = {}

            # Name + link
            name_node = row.css_first("td.hauptlink a")
            if not name_node:
                continue
            player["name"] = name_node.text(strip=True)
            href = name_node.attributes.get("href", "")
            id_match = re.search(r"/(\d+)$", href)
            if id_match:
                player["transfermarkt_id"] = id_match.group(1)
            slug_match = re.match(r"/([^/]+)/", href)
            if slug_match:
                player["slug"] = slug_match.group(1)

            # Jersey number
            number_node = row.css_first("div.rn_nummer")
            if number_node:
                try:
                    player["jersey_number"] = int(number_node.text(strip=True))
                except ValueError:
                    pass

            # Position
            pos_node = row.css_first("td.posrela table tr:last-child td")
            if pos_node:
                player["position"] = pos_node.text(strip=True)

            # Age / DoB
            dob_node = row.css_first("td:nth-child(3)")
            if dob_node:
                player["dob_raw"] = dob_node.text(strip=True)

            # Nationality
            nat_imgs = row.css("img.flaggenrahmen")
            if nat_imgs:
                player["nationalities"] = [img.attributes.get("title", "") for img in nat_imgs]

            # Market value
            mv_node = row.css_first("td.rechts.hauptlink a")
            if mv_node:
                raw_mv = mv_node.text(strip=True)
                player["market_value_raw"] = raw_mv
                player["market_value_eur"] = self._parse_value(raw_mv)

            players.append(player)

        return players

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _parse_value(self, value_str: str) -> Optional[int]:
        """
        Convert Transfermarkt value strings to integer euros.
        Examples:
          "€45m"    → 45_000_000
          "€850k"   → 850_000
          "€1.50m"  → 1_500_000
          "?"       → None
          "free"    → 0
        """
        if not value_str:
            return None

        v = value_str.lower().strip()

        if v in ("?", "-", "n/a", "undisclosed"):
            return None
        if "free" in v:
            return 0

        # Remove currency symbols
        v = v.replace("€", "").replace("£", "").replace("$", "").replace(",", ".").strip()

        try:
            if "bn" in v:
                return int(float(v.replace("bn", "").strip()) * 1_000_000_000)
            elif "m" in v:
                return int(float(v.replace("m", "").strip()) * 1_000_000)
            elif "k" in v:
                return int(float(v.replace("k", "").strip()) * 1_000)
            else:
                return int(float(v))
        except (ValueError, TypeError):
            return None

    async def scrape(self, club_slug: str, club_id: int) -> dict:
        """Scrape full club data: squad + individual player values."""
        self.log(f"Scraping club {club_slug} (ID: {club_id})")

        squad = await self.get_squad(club_slug, club_id)
        self.log(f"Found {len(squad)} players in squad")

        players_data = []
        for player in squad:
            tm_id = player.get("transfermarkt_id")
            slug  = player.get("slug")
            if not tm_id or not slug:
                continue

            profile  = await self.get_player_profile(slug, int(tm_id))
            mv_hist  = await self.get_market_value_history(slug, int(tm_id))
            transfers= await self.get_transfer_history(slug, int(tm_id))

            players_data.append({
                "squad_info":   player,
                "profile":      profile,
                "market_values": mv_hist,
                "transfers":    transfers,
            })

        return {
            "club_slug":  club_slug,
            "club_id":    club_id,
            "squad":      squad,
            "players":    players_data,
        }
