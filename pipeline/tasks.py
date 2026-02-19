"""Celery tasks for scheduled ingestion and failed-job reprocessing."""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timedelta, timezone

from celery.utils.log import get_task_logger
from sqlalchemy import func, select, text

from db.models import ScrapeJob
from db.session import get_sync_session
from pipeline.celery_app import celery_app
from pipeline.data_quality import run_data_quality_checks
from pipeline.kpis import snapshot_content_priorities, snapshot_core_kpis
from pipeline.runner import CURRENT_SEASONS

logger = get_task_logger(__name__)


def _run_runner_command(args: list[str]) -> tuple[int, str]:
    cmd = [sys.executable, "-m", "pipeline.runner", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode, output.strip()


@celery_app.task(name="pipeline.run_competition_job")
def run_competition_job(competition_key: str, season_id: int | None = None) -> dict:
    season = season_id or CURRENT_SEASONS.get(competition_key)
    if not season:
        msg = f"No season configured for competition '{competition_key}'"
        logger.error(msg)
        return {"ok": False, "competition": competition_key, "error": msg}

    rc, output = _run_runner_command(["--competition", competition_key, "--season", str(season)])
    if rc != 0:
        logger.error("Competition job failed: %s | %s", competition_key, output)
        return {"ok": False, "competition": competition_key, "season": season, "error": output}

    logger.info("Competition job success: %s / %s", competition_key, season)
    return {"ok": True, "competition": competition_key, "season": season}


@celery_app.task(name="pipeline.reprocess_failed_jobs")
def reprocess_failed_jobs(limit: int = 10, max_retry_count: int = 3, max_age_hours: int = 48) -> dict:
    """
    Reprocess failed jobs as dead-letter strategy:
    - retry failed jobs up to max_retry_count
    - once exceeded, mark as dead_letter
    """
    now = datetime.now(timezone.utc)
    min_started = now - timedelta(hours=max_age_hours)

    retried = 0
    dead_lettered = 0

    with get_sync_session() as session:
        stmt = (
            select(ScrapeJob)
            .where(
                ScrapeJob.status == "failed",
                ScrapeJob.started_at.is_not(None),
                ScrapeJob.started_at >= min_started,
            )
            .order_by(ScrapeJob.started_at.desc())
            .limit(limit)
        )
        failed_jobs = list(session.execute(stmt).scalars().all())

        for job in failed_jobs:
            if job.retry_count >= max_retry_count:
                job.status = "dead_letter"
                dead_lettered += 1
                continue

            parts = (job.entity_id or "").split(":")
            if len(parts) != 2:
                job.retry_count += 1
                job.error_message = f"Invalid entity_id format for retry: {job.entity_id}"
                continue

            competition_key = parts[0]
            try:
                season_id = int(parts[1])
            except ValueError:
                job.retry_count += 1
                job.error_message = f"Invalid season_id in entity_id: {job.entity_id}"
                continue

            rc, output = _run_runner_command(["--competition", competition_key, "--season", str(season_id)])
            job.retry_count += 1
            if rc == 0:
                retried += 1
                job.status = "reprocessed"
                job.error_message = None
            else:
                job.error_message = output
                if job.retry_count >= max_retry_count:
                    job.status = "dead_letter"
                    dead_lettered += 1

    logger.info(
        "Reprocess summary: retried=%s dead_lettered=%s checked=%s",
        retried,
        dead_lettered,
        len(failed_jobs),
    )
    return {"retried": retried, "dead_lettered": dead_lettered, "checked": len(failed_jobs)}


@celery_app.task(name="pipeline.refresh_data_marts")
def refresh_data_marts() -> dict:
    with get_sync_session() as session:
        session.execute(text("REFRESH MATERIALIZED VIEW analytics.dm_scouting_player_season"))
        session.execute(text("REFRESH MATERIALIZED VIEW analytics.dm_betting_team_form"))
        session.execute(text("REFRESH MATERIALIZED VIEW analytics.dm_content_team_trending"))
        session.execute(text("REFRESH MATERIALIZED VIEW analytics.dm_content_player_trending"))
        session.execute(text("REFRESH MATERIALIZED VIEW analytics.dm_content_match_intensity"))
    logger.info("Data marts refreshed.")
    return {"ok": True}


@celery_app.task(name="pipeline.run_data_quality_checks")
def run_data_quality_checks_task() -> dict:
    summary = run_data_quality_checks()
    logger.info("Data quality checks completed: %s", summary)
    return summary


@celery_app.task(name="pipeline.monitor_operational_health")
def monitor_operational_health(max_failed_per_hour: int = 3, max_avg_latency_sec: int = 900) -> dict:
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)

    with get_sync_session() as session:
        failed = session.execute(
            select(func.count(ScrapeJob.id)).where(
                ScrapeJob.status == "failed",
                ScrapeJob.started_at.is_not(None),
                ScrapeJob.started_at >= one_hour_ago,
            )
        ).scalar_one()

        success = session.execute(
            select(func.count(ScrapeJob.id)).where(
                ScrapeJob.status == "success",
                ScrapeJob.started_at.is_not(None),
                ScrapeJob.started_at >= one_hour_ago,
            )
        ).scalar_one()

        avg_latency = session.execute(
            select(
                func.avg(
                    func.extract("epoch", ScrapeJob.finished_at - ScrapeJob.started_at)
                )
            ).where(
                ScrapeJob.finished_at.is_not(None),
                ScrapeJob.started_at.is_not(None),
                ScrapeJob.started_at >= one_hour_ago,
            )
        ).scalar_one()

    avg_latency_value = float(avg_latency) if avg_latency is not None else 0.0
    alerts = []
    if failed > max_failed_per_hour:
        alerts.append(f"High failed jobs in last hour: {failed} > {max_failed_per_hour}")
    if success == 0:
        alerts.append("No successful jobs in last hour.")
    if avg_latency_value > max_avg_latency_sec:
        alerts.append(
            f"High average job latency in last hour: {avg_latency_value:.1f}s > {max_avg_latency_sec}s"
        )

    if alerts:
        for alert in alerts:
            logger.error("ALERT %s", alert)
    else:
        logger.info(
            "Operational health OK | success_1h=%s failed_1h=%s avg_latency_1h=%.1fs",
            success,
            failed,
            avg_latency_value,
        )

    return {
        "ok": len(alerts) == 0,
        "alerts": alerts,
        "success_1h": int(success),
        "failed_1h": int(failed),
        "avg_latency_1h": avg_latency_value,
    }


@celery_app.task(name="pipeline.snapshot_core_kpis")
def snapshot_core_kpis_task(window_hours: int = 24) -> dict:
    summary = snapshot_core_kpis(window_hours=window_hours)
    logger.info("KPI snapshot completed: %s", summary["kpis"])
    return summary


@celery_app.task(name="pipeline.snapshot_content_priorities")
def snapshot_content_priorities_task(days: int = 30, target_min_ratio: float | None = None) -> dict:
    report = snapshot_content_priorities(days=days, target_min_ratio=target_min_ratio)
    logger.info(
        "Content priorities snapshot completed: breaches=%s total=%s",
        report["breach_count"],
        report["count"],
    )
    return report
