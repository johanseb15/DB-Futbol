"""
Seed script: loads reference data (countries + competitions catalog).

Run once after DB initialization:
  python scripts/seed.py
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from db.session import get_async_session
from db.models import Country, Competition


COUNTRIES = [
    {"name": "Argentina",         "code_iso2": "AR", "code_iso3": "ARG", "continent": "South America"},
    {"name": "Brazil",            "code_iso2": "BR", "code_iso3": "BRA", "continent": "South America"},
    {"name": "Uruguay",           "code_iso2": "UY", "code_iso3": "URY", "continent": "South America"},
    {"name": "Colombia",          "code_iso2": "CO", "code_iso3": "COL", "continent": "South America"},
    {"name": "Chile",             "code_iso2": "CL", "code_iso3": "CHL", "continent": "South America"},
    {"name": "England",           "code_iso2": "GB", "code_iso3": "ENG", "continent": "Europe"},
    {"name": "Spain",             "code_iso2": "ES", "code_iso3": "ESP", "continent": "Europe"},
    {"name": "Germany",           "code_iso2": "DE", "code_iso3": "DEU", "continent": "Europe"},
    {"name": "Italy",             "code_iso2": "IT", "code_iso3": "ITA", "continent": "Europe"},
    {"name": "France",            "code_iso2": "FR", "code_iso3": "FRA", "continent": "Europe"},
    {"name": "Portugal",          "code_iso2": "PT", "code_iso3": "PRT", "continent": "Europe"},
    {"name": "Netherlands",       "code_iso2": "NL", "code_iso3": "NLD", "continent": "Europe"},
    {"name": "Belgium",           "code_iso2": "BE", "code_iso3": "BEL", "continent": "Europe"},
]

COMPETITIONS_SEED = [
    # Argentina
    {
        "name": "Liga Profesional",     "short_name": "LPF",
        "type": "league", "level": 1,   "sofascore_id": 155,
        "country_code": "AR",
    },
    {
        "name": "Primera Nacional",     "short_name": "PN",
        "type": "league", "level": 2,   "sofascore_id": 703,
        "country_code": "AR",
    },
    {
        "name": "Copa Argentina",       "short_name": "Copa AR",
        "type": "cup",   "level": 1,    "sofascore_id": 329,
        "country_code": "AR",
    },

    # England
    {
        "name": "Premier League",       "short_name": "EPL",
        "type": "league", "level": 1,   "sofascore_id": 17,
        "country_code": "GB",
    },

    # Spain
    {
        "name": "La Liga",              "short_name": "LaLiga",
        "type": "league", "level": 1,   "sofascore_id": 8,
        "country_code": "ES",
    },

    # Italy
    {
        "name": "Serie A",              "short_name": "SerieA",
        "type": "league", "level": 1,   "sofascore_id": 23,
        "country_code": "IT",
    },

    # Germany
    {
        "name": "Bundesliga",           "short_name": "BL",
        "type": "league", "level": 1,   "sofascore_id": 35,
        "country_code": "DE",
    },

    # France
    {
        "name": "Ligue 1",              "short_name": "L1",
        "type": "league", "level": 1,   "sofascore_id": 34,
        "country_code": "FR",
    },

    # International
    {
        "name": "UEFA Champions League","short_name": "UCL",
        "type": "international", "level": 1, "sofascore_id": 7,
        "country_code": None,
    },
]


async def seed():
    logger.info("Seeding reference data...")

    async with get_async_session() as session:
        # ── Countries ──────────────────────────────────────────────────────
        logger.info("Seeding countries...")
        country_map = {}

        for c in COUNTRIES:
            from sqlalchemy import select
            result = await session.execute(
                select(Country).where(Country.code_iso2 == c["code_iso2"])
            )
            existing = result.scalar_one_or_none()
            if not existing:
                country = Country(**c)
                session.add(country)
                await session.flush()
                country_map[c["code_iso2"]] = country.id
                logger.debug(f"  + {c['name']}")
            else:
                country_map[c["code_iso2"]] = existing.id
                logger.debug(f"  ~ {c['name']} (exists)")

        # ── Competitions ───────────────────────────────────────────────────
        logger.info("Seeding competitions...")
        for comp_data in COMPETITIONS_SEED:
            from sqlalchemy import select
            result = await session.execute(
                select(Competition).where(Competition.sofascore_id == comp_data["sofascore_id"])
            )
            existing = result.scalar_one_or_none()

            if not existing:
                country_code = comp_data.pop("country_code", None)
                country_id = country_map.get(country_code) if country_code else None

                comp = Competition(
                    country_id=country_id,
                    **comp_data
                )
                session.add(comp)
                logger.debug(f"  + {comp_data['name']}")
            else:
                logger.debug(f"  ~ {comp_data['name']} (exists)")

    logger.success("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
