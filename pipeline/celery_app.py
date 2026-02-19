"""Celery app and beat schedule for production pipeline jobs."""
from celery import Celery
from celery.schedules import crontab

from config.settings import settings


celery_app = Celery(
    "football_pipeline",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["pipeline.tasks"],
)

celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
    beat_schedule={
        # Staggered schedules to reduce spikes and keep each run independent.
        "comp-arg-liga-profesional": {
            "task": "pipeline.run_competition_job",
            "schedule": 15 * 60,
            "args": ("arg_liga_profesional",),
        },
        "comp-eng-premier-league": {
            "task": "pipeline.run_competition_job",
            "schedule": 20 * 60,
            "args": ("eng_premier_league",),
        },
        "comp-esp-la-liga": {
            "task": "pipeline.run_competition_job",
            "schedule": 25 * 60,
            "args": ("esp_la_liga",),
        },
        "comp-ita-serie-a": {
            "task": "pipeline.run_competition_job",
            "schedule": 30 * 60,
            "args": ("ita_serie_a",),
        },
        "comp-ger-bundesliga": {
            "task": "pipeline.run_competition_job",
            "schedule": 35 * 60,
            "args": ("ger_bundesliga",),
        },
        "comp-fra-ligue-1": {
            "task": "pipeline.run_competition_job",
            "schedule": 40 * 60,
            "args": ("fra_ligue_1",),
        },
        "comp-ucl": {
            "task": "pipeline.run_competition_job",
            "schedule": 45 * 60,
            "args": ("ucl",),
        },
        "retry-failed-jobs": {
            "task": "pipeline.reprocess_failed_jobs",
            "schedule": 10 * 60,
        },
        "ops-health-monitor": {
            "task": "pipeline.monitor_operational_health",
            "schedule": 5 * 60,
        },
        "daily-data-quality": {
            "task": "pipeline.run_data_quality_checks",
            "schedule": crontab(hour=3, minute=0),
        },
        "daily-refresh-data-marts": {
            "task": "pipeline.refresh_data_marts",
            "schedule": crontab(hour=3, minute=20),
        },
        "daily-kpi-snapshot": {
            "task": "pipeline.snapshot_core_kpis",
            "schedule": crontab(hour=3, minute=40),
            "args": (24,),
        },
        "daily-content-priorities": {
            "task": "pipeline.snapshot_content_priorities",
            "schedule": crontab(hour=3, minute=50),
            "args": (30,),
        },
    },
)
