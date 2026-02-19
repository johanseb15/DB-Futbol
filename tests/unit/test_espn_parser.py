import json
from pathlib import Path

from scrapers.espn.scraper import ESPNFallbackScraper


def test_espn_event_to_sofascore_like_shape():
    fixture_path = Path("tests/fixtures/espn_scoreboard_event.json")
    event = json.loads(fixture_path.read_text(encoding="utf-8"))

    scraper = ESPNFallbackScraper()
    parsed = scraper._to_sofascore_like_match(event, season_id=2026)

    assert parsed is not None
    assert parsed["match"]["id"] == 734521
    assert parsed["match"]["homeTeam"]["name"] == "Talleres"
    assert parsed["match"]["awayTeam"]["name"] == "River Plate"
    assert parsed["match"]["homeScore"]["current"] == 2
    assert parsed["match"]["awayScore"]["current"] == 1
    assert parsed["match"]["status"]["type"] == "finished"

