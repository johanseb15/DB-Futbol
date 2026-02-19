"""
Main pipeline runner.

Orchestrates the full data ingestion flow:
  1. Scrape raw data from sources
  2. Store raw payloads in scrape_raw table
  3. Normalize into clean tables
  4. Update scrape_jobs with results
"""
import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone

import redis.asyncio as aioredis
from loguru import logger
from sqlalchemy import desc, select

from config.settings import settings
from db.models import ScrapeJob, ScrapeRaw
from db.session import check_connection, create_all_tables, get_async_session
from pipeline.normalizer import SofascoreNormalizer
from scrapers.espn.scraper import ESPNFallbackScraper
from scrapers.sofascore.scraper import COMPETITIONS, SofascoreScraper


CURRENT_SEASONS = {
    "arg_liga_profesional": 62063,   # 2024
    "arg_primera_nacional": 58889,   # 2024
    "arg_copa_argentina": 58890,     # 2024
    "eng_premier_league": 61643,     # 2024/25
    "esp_la_liga": 61643,            # update with correct ID
    "ita_serie_a": 57524,
    "ger_bundesliga": 58766,
    "fra_ligue_1": 57346,
    "ucl": 61644,
}


def _payload_fingerprint(payload: dict) -> str:
    normalized = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _emit_metric(event: str, **fields) -> None:
    payload = {"event": event, "ts": datetime.now(timezone.utc).isoformat(), **fields}
    logger.info(json.dumps(payload, ensure_ascii=True, sort_keys=True))


def _validate_raw_payload(payload: dict) -> tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "Payload is not a dictionary."
    if "matches" not in payload:
        return False, "Payload does not include 'matches'."
    if not isinstance(payload.get("matches"), list):
        return False, "'matches' must be a list."
    if len(payload["matches"]) > 0 and not isinstance(payload["matches"][0], dict):
        return False, "Each match entry must be an object."
    return True, ""


async def _mark_job_failed(job_id, reason: str) -> None:
    async with get_async_session() as session:
        result = await session.get(ScrapeJob, job_id)
        if result:
            result.status = "failed"
            result.error_message = reason
            result.finished_at = datetime.now(timezone.utc)


async def _store_raw_payload(job_id, source: str, entity_id: str, payload: dict) -> bool:
    """
    Store payload only if it's different from the latest payload for the same entity.
    Returns True if inserted, False if deduplicated.
    """
    new_fp = _payload_fingerprint(payload)
    async with get_async_session() as session:
        stmt = (
            select(ScrapeRaw)
            .where(
                ScrapeRaw.source == source,
                ScrapeRaw.entity_type == "competition_season",
                ScrapeRaw.entity_id == entity_id,
            )
            .order_by(desc(ScrapeRaw.scraped_at))
            .limit(1)
        )
        latest = (await session.execute(stmt)).scalar_one_or_none()

        if latest:
            latest_fp = _payload_fingerprint(latest.payload)
            if latest_fp == new_fp:
                logger.info(f"Raw payload deduplicated for {entity_id} (identical to previous).")
                return False

        session.add(
            ScrapeRaw(
                job_id=job_id,
                source=source,
                entity_type="competition_season",
                entity_id=entity_id,
                payload=payload,
            )
        )
        return True


async def _update_job_source(job_id, source: str) -> None:
    async with get_async_session() as session:
        result = await session.get(ScrapeJob, job_id)
        if result:
            result.source = source


async def run_competition(competition_key: str, season_id: int, redis_client) -> dict:
    """Run full pipeline for one competition season."""
    logger.info(f"Starting pipeline: {competition_key} / season {season_id}")
    _emit_metric("job_start", competition=competition_key, season=season_id)

    total_stats = {"matches": 0, "errors": 0, "duration_s": 0}
    start_time = datetime.now(timezone.utc)
    entity_id = f"{competition_key}:{season_id}"

    async with get_async_session() as session:
        job = ScrapeJob(
            source="sofascore",
            entity_type="competition_season",
            entity_id=entity_id,
            status="running",
            started_at=start_time,
        )
        session.add(job)
        await session.flush()
        job_id = job.id

    active_source = "sofascore"
    async with SofascoreScraper(redis_client=redis_client) as scraper:
        try:
            raw_data = await scraper.scrape(competition_key, season_id)
        except Exception as e:
            logger.error(f"Sofascore scrape failed for {competition_key}: {e}")
            raw_data = None

    if raw_data is None or not raw_data.get("matches"):
        logger.warning(
            f"Sofascore returned no matches for {competition_key}:{season_id}. "
            "Trying ESPN fallback."
        )
        async with ESPNFallbackScraper(redis_client=redis_client) as fallback:
            try:
                raw_data = await fallback.scrape(competition_key, season_id)
                active_source = "espn_fallback"
            except Exception as e:
                logger.error(f"ESPN fallback failed for {competition_key}: {e}")
                await _mark_job_failed(job_id, f"Sofascore empty/failed and ESPN fallback failed: {e}")
                _emit_metric(
                    "job_failed",
                    competition=competition_key,
                    season=season_id,
                    source="espn_fallback",
                    reason=str(e),
                )
                return total_stats

    valid, reason = _validate_raw_payload(raw_data)
    if not valid:
        logger.error(f"Invalid raw payload for {entity_id}: {reason}")
        await _mark_job_failed(job_id, reason)
        _emit_metric(
            "job_failed",
            competition=competition_key,
            season=season_id,
            source=active_source,
            reason=reason,
        )
        return total_stats

    await _update_job_source(job_id, active_source)

    inserted = await _store_raw_payload(job_id, active_source, entity_id, raw_data)
    if inserted:
        logger.info(f"Raw payload stored for {entity_id}.")

    logger.info(f"Normalizing {len(raw_data.get('matches', []))} matches...")

    async with get_async_session() as session:
        normalizer = SofascoreNormalizer(session)
        stats = await normalizer.normalize_full_scrape(raw_data)

    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()

    async with get_async_session() as session:
        result = await session.get(ScrapeJob, job_id)
        if result:
            result.status = "success" if stats["errors"] == 0 else "failed"
            result.finished_at = end_time
            result.normalized = True
            result.normalized_at = end_time

    total_stats.update(stats)
    total_stats["duration_s"] = round(duration, 1)

    logger.success(
        f"Pipeline complete: {competition_key} | "
        f"matches={stats['matches']} errors={stats['errors']} time={duration:.1f}s"
    )
    _emit_metric(
        "job_complete",
        competition=competition_key,
        season=season_id,
        source=active_source,
        matches=stats["matches"],
        errors=stats["errors"],
        duration_s=round(duration, 1),
    )

    return total_stats


async def discover_current_seasons(competition_key: str) -> list[dict]:
    """Fetch and display available seasons for a competition."""
    comp = COMPETITIONS.get(competition_key)
    if not comp:
        logger.error(f"Unknown competition: {competition_key}")
        return []

    async with SofascoreScraper() as scraper:
        seasons = await scraper.get_seasons(comp["id"])

    source = "sofascore"
    if not seasons:
        logger.warning(f"Sofascore discover returned no seasons for {competition_key}. Trying ESPN fallback.")
        async with ESPNFallbackScraper() as fallback:
            seasons = await fallback.discover_seasons(competition_key)
            source = "espn_fallback"

    logger.info(f"Available seasons for {comp['name']} (source={source}):")
    for season in seasons[:10]:
        logger.info(f"  ID: {season.get('id')} | Year: {season.get('year')}")

    return seasons


async def main():
    parser = argparse.ArgumentParser(description="Football data pipeline")
    parser.add_argument("--competition", type=str, help="Competition key (e.g. arg_liga_profesional)")
    parser.add_argument("--season", type=int, help="Sofascore season ID")
    parser.add_argument("--all", action="store_true", help="Run all competitions")
    parser.add_argument("--discover", type=str, help="Discover seasons for a competition")
    parser.add_argument("--init-db", action="store_true", help="Initialize database tables")
    args = parser.parse_args()

    logger.add(settings.LOG_FILE, rotation="100 MB", level=settings.LOG_LEVEL)

    if args.init_db:
        logger.info("Initializing database via Alembic...")
        proc = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            logger.error("Alembic upgrade failed, fallback to create_all_tables for compatibility.")
            if proc.stdout:
                logger.error(proc.stdout.strip())
            if proc.stderr:
                logger.error(proc.stderr.strip())
            await create_all_tables()
            logger.success("Tables created with create_all fallback.")
        else:
            logger.success("Alembic upgrade head completed.")
        return

    if not await check_connection():
        logger.error("Cannot connect to database. Is PostgreSQL running?")
        return

    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        if args.discover:
            await discover_current_seasons(args.discover)
            return

        if args.competition:
            season_id = args.season or CURRENT_SEASONS.get(args.competition)
            if not season_id:
                logger.error(f"No season ID provided. Use --season or run --discover {args.competition}")
                return
            await run_competition(args.competition, season_id, redis_client)
            return

        if args.all:
            logger.info(f"Running all {len(CURRENT_SEASONS)} competitions")
            all_stats = []
            for comp_key, season_id in CURRENT_SEASONS.items():
                stats = await run_competition(comp_key, season_id, redis_client)
                all_stats.append({"competition": comp_key, **stats})

            logger.success("All pipelines complete:")
            for stat in all_stats:
                logger.info(f"  {stat['competition']}: matches={stat['matches']} errors={stat['errors']}")
            return

        parser.print_help()
    finally:
        await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
