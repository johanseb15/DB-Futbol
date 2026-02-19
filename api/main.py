"""Internal read-only API for analytics consumers."""

from __future__ import annotations

import hashlib
import secrets
import time
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Optional, TypedDict

import redis as redis_sync
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import Counter, Gauge, generate_latest
from sqlalchemy import func, select, text

from config.settings import settings
from db.models import (
    APIClient,
    APIRequestUsage,
    ContentPriorityReport,
    DataQualityIssue,
    KPIDailySnapshot,
    Match,
    Player,
    PlayerMatchStats,
    ScrapeJob,
    Team,
)
from db.session import get_sync_session
from pipeline.kpis import (
    collect_content_coverage_by_competition,
    collect_core_kpis,
    collect_coverage_by_competition,
    snapshot_content_priorities,
    snapshot_core_kpis,
)

app = FastAPI(title="Football Internal API", version="0.2.0")

_cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = redis_sync.from_url(settings.REDIS_URL, decode_responses=True)

api_requests_total = Counter("api_requests_total", "Total API requests", ["endpoint"])
players_total_gauge = Gauge("players_total", "Total players")
teams_total_gauge = Gauge("teams_total", "Total teams")
matches_total_gauge = Gauge("matches_total", "Total matches")
scrape_jobs_success_gauge = Gauge("scrape_jobs_success_total", "Total successful scrape jobs")
scrape_jobs_failed_gauge = Gauge("scrape_jobs_failed_total", "Total failed scrape jobs")
scrape_jobs_avg_latency_gauge = Gauge("scrape_jobs_avg_latency_seconds", "Average scrape job latency in seconds")
source_failed_jobs_gauge = Gauge("scrape_source_failed_jobs_total", "Failed scrape jobs by source", ["source"])


def _inc(endpoint: str) -> None:
    api_requests_total.labels(endpoint=endpoint).inc()


def _request_category(path: str) -> str:
    if path.startswith("/mart/") or path.startswith("/v1/content/"):
        return "mart"
    if path in {"/players", "/teams", "/matches", "/stats"} or path.startswith("/raw/"):
        return "raw"
    return "core"


def _is_premium_path(path: str) -> bool:
    return path.startswith("/v1/content/") or path.startswith("/kpi/content/")


def _hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _safe_iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _parse_uuid(value: str, field_name: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name} UUID.") from exc


def _query_mart(sql: str, params: dict[str, Any]) -> dict[str, Any]:
    with get_sync_session() as session:
        rows = session.execute(text(sql), params).mappings().all()
    return {"count": len(rows), "items": [dict(r) for r in rows]}


def _query_mart_or_503(sql: str, params: dict[str, Any], name: str) -> dict[str, Any]:
    try:
        return _query_mart(sql, params)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"{name} unavailable: {exc}") from exc


class ResolvedAPIClient(TypedDict):
    id: uuid.UUID
    plan: str
    rate_limit_per_minute: int


def _resolve_api_client(raw_key: Optional[str]) -> Optional[ResolvedAPIClient]:
    if not raw_key:
        return None
    key_hash = _hash_api_key(raw_key)
    with get_sync_session() as session:
        stmt = select(APIClient).where(APIClient.key_hash == key_hash, APIClient.is_active.is_(True))
        client = session.execute(stmt).scalars().first()
        if not client:
            return None
        return {
            "id": client.id,
            "plan": client.plan,
            "rate_limit_per_minute": int(client.rate_limit_per_minute or 0),
        }


def _enforce_rate_limit(client: ResolvedAPIClient) -> None:
    if not settings.API_RATE_LIMIT_ENABLED:
        return

    limit = client["rate_limit_per_minute"] or settings.API_DEFAULT_RATE_LIMIT_PER_MINUTE
    bucket = int(time.time() // 60)
    key = f"rl:{client['id']}:{bucket}"

    try:
        current = redis_client.incr(key)
        if current == 1:
            redis_client.expire(key, 70)
        if int(current) > int(limit):
            raise HTTPException(status_code=429, detail="Rate limit exceeded for API plan.")
    except HTTPException:
        raise
    except Exception:
        # Fail-open if redis is unavailable to avoid hard downtime.
        return


def _refresh_pipeline_metrics() -> None:
    with get_sync_session() as session:
        success_total = session.execute(
            select(func.count(ScrapeJob.id)).where(ScrapeJob.status == "success")
        ).scalar_one()
        failed_total = session.execute(
            select(func.count(ScrapeJob.id)).where(ScrapeJob.status.in_(["failed", "dead_letter"]))
        ).scalar_one()
        avg_latency = session.execute(
            select(func.avg(func.extract("epoch", ScrapeJob.finished_at - ScrapeJob.started_at))).where(
                ScrapeJob.finished_at.is_not(None),
                ScrapeJob.started_at.is_not(None),
            )
        ).scalar_one()
        failed_by_source = session.execute(
            select(ScrapeJob.source, func.count(ScrapeJob.id))
            .where(ScrapeJob.status.in_(["failed", "dead_letter"]))
            .group_by(ScrapeJob.source)
        ).all()

    scrape_jobs_success_gauge.set(int(success_total))
    scrape_jobs_failed_gauge.set(int(failed_total))
    scrape_jobs_avg_latency_gauge.set(float(avg_latency or 0.0))
    source_failed_jobs_gauge.clear()
    for source, count in failed_by_source:
        source_failed_jobs_gauge.labels(source=str(source or "unknown")).set(int(count))


@app.middleware("http")
async def track_request_usage(request: Request, call_next):
    path = request.url.path
    api_key = request.headers.get(settings.API_KEY_HEADER)
    client = _resolve_api_client(api_key)

    if _is_premium_path(path):
        if settings.API_KEY_ENFORCE_PREMIUM and not client:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": f"Missing or invalid API key for premium endpoint. Use header {settings.API_KEY_HEADER}."
                },
            )
        if client:
            try:
                _enforce_rate_limit(client)
            except HTTPException as exc:
                return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    response = await call_next(request)

    if path not in {"/metrics", "/health"}:
        with get_sync_session() as session:
            session.add(
                APIRequestUsage(
                    endpoint=path,
                    category=_request_category(path),
                    method=request.method,
                    status_code=int(response.status_code),
                    api_client_id=client["id"] if client else None,
                    api_plan=client["plan"] if client else None,
                )
            )

    return response


@app.get("/health")
def health() -> dict[str, str]:
    _inc("/health")
    return {"status": "ok"}


@app.get("/players")
def list_players(limit: int = Query(default=50, ge=1, le=1000), offset: int = Query(default=0, ge=0)):
    _inc("/players")
    with get_sync_session() as session:
        stmt = select(Player).order_by(Player.name.asc()).offset(offset).limit(limit)
        rows = session.execute(stmt).scalars().all()
        total = session.execute(select(func.count(Player.id))).scalar_one()

    players_total_gauge.set(total)
    return {
        "total": total,
        "count": len(rows),
        "items": [
            {
                "id": str(p.id),
                "name": p.name,
                "position": p.position,
                "sofascore_id": p.sofascore_id,
                "transfermarkt_id": p.transfermarkt_id,
            }
            for p in rows
        ],
    }


@app.get("/teams")
def list_teams(limit: int = Query(default=50, ge=1, le=1000), offset: int = Query(default=0, ge=0)):
    _inc("/teams")
    with get_sync_session() as session:
        stmt = select(Team).order_by(Team.name.asc()).offset(offset).limit(limit)
        rows = session.execute(stmt).scalars().all()
        total = session.execute(select(func.count(Team.id))).scalar_one()

    teams_total_gauge.set(total)
    return {
        "total": total,
        "count": len(rows),
        "items": [
            {
                "id": str(t.id),
                "name": t.name,
                "short_name": t.short_name,
                "sofascore_id": t.sofascore_id,
                "transfermarkt_id": t.transfermarkt_id,
            }
            for t in rows
        ],
    }


@app.get("/matches")
def list_matches(
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = None,
):
    _inc("/matches")
    with get_sync_session() as session:
        stmt = select(Match).order_by(Match.kickoff_time.desc().nullslast()).offset(offset).limit(limit)
        if status:
            stmt = stmt.where(Match.status == status)
        rows = session.execute(stmt).scalars().all()
        total = session.execute(select(func.count(Match.id))).scalar_one()

    matches_total_gauge.set(total)
    return {
        "total": total,
        "count": len(rows),
        "items": [
            {
                "id": str(m.id),
                "season_id": str(m.season_id),
                "home_team_id": str(m.home_team_id),
                "away_team_id": str(m.away_team_id),
                "kickoff_time": _safe_iso(m.kickoff_time),
                "status": m.status,
                "home_score": m.home_score,
                "away_score": m.away_score,
                "sofascore_id": m.sofascore_id,
            }
            for m in rows
        ],
    }


@app.get("/stats")
def player_stats(
    player_id: Optional[str] = None,
    team_id: Optional[str] = None,
    season_id: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000),
):
    _inc("/stats")
    with get_sync_session() as session:
        stmt = select(PlayerMatchStats).order_by(PlayerMatchStats.created_at.desc()).limit(limit)
        if player_id:
            stmt = stmt.where(PlayerMatchStats.player_id == player_id)
        if team_id:
            stmt = stmt.where(PlayerMatchStats.team_id == team_id)
        if season_id:
            stmt = stmt.join(Match, Match.id == PlayerMatchStats.match_id).where(Match.season_id == season_id)

        rows = session.execute(stmt).scalars().all()

    return {
        "count": len(rows),
        "items": [
            {
                "match_id": str(s.match_id),
                "player_id": str(s.player_id),
                "team_id": str(s.team_id),
                "minutes_played": s.minutes_played,
                "goals": s.goals,
                "assists": s.assists,
                "shots": s.shots,
                "rating": s.rating,
            }
            for s in rows
        ],
    }


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    _inc("/metrics")
    _refresh_pipeline_metrics()
    return PlainTextResponse(generate_latest().decode("utf-8"))


@app.get("/quality/issues")
def list_data_quality_issues(
    limit: int = Query(default=100, ge=1, le=1000),
    severity: Optional[str] = None,
    check_name: Optional[str] = None,
):
    _inc("/quality/issues")
    with get_sync_session() as session:
        stmt = select(DataQualityIssue).order_by(DataQualityIssue.detected_at.desc()).limit(limit)
        if severity:
            stmt = stmt.where(DataQualityIssue.severity == severity)
        if check_name:
            stmt = stmt.where(DataQualityIssue.check_name == check_name)
        rows = session.execute(stmt).scalars().all()

    return {
        "count": len(rows),
        "items": [
            {
                "id": str(i.id),
                "check_name": i.check_name,
                "severity": i.severity,
                "entity_type": i.entity_type,
                "entity_id": i.entity_id,
                "issue_count": i.issue_count,
                "message": i.message,
                "detected_at": i.detected_at.isoformat(),
            }
            for i in rows
        ],
    }


@app.get("/quality/summary")
def data_quality_summary() -> dict[str, Any]:
    _inc("/quality/summary")
    with get_sync_session() as session:
        by_check = session.execute(
            select(DataQualityIssue.check_name, func.count(DataQualityIssue.id))
            .group_by(DataQualityIssue.check_name)
            .order_by(func.count(DataQualityIssue.id).desc())
        ).all()
        by_severity = session.execute(
            select(DataQualityIssue.severity, func.count(DataQualityIssue.id))
            .group_by(DataQualityIssue.severity)
            .order_by(func.count(DataQualityIssue.id).desc())
        ).all()
        total = session.execute(select(func.count(DataQualityIssue.id))).scalar_one()

    return {
        "total": int(total),
        "by_check": [{"check_name": c, "count": int(n)} for c, n in by_check],
        "by_severity": [{"severity": s, "count": int(n)} for s, n in by_severity],
    }


@app.get("/mart/scouting")
def mart_scouting(
    season_id: Optional[str] = None,
    team_id: Optional[str] = None,
    limit: int = Query(default=200, ge=1, le=1000),
):
    _inc("/mart/scouting")
    where_parts = []
    params: dict[str, Any] = {"limit": limit}
    if season_id:
        where_parts.append("season_id = CAST(:season_id AS uuid)")
        params["season_id"] = season_id
    if team_id:
        where_parts.append("team_id = CAST(:team_id AS uuid)")
        params["team_id"] = team_id

    where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
    sql = f"""
        SELECT
            season_id::text AS season_id,
            player_id::text AS player_id,
            team_id::text AS team_id,
            matches,
            minutes_played,
            goals,
            assists,
            avg_rating,
            shots
        FROM analytics.dm_scouting_player_season
        {where_sql}
        ORDER BY avg_rating DESC NULLS LAST, goals DESC NULLS LAST
        LIMIT :limit
    """
    return _query_mart_or_503(sql, params, "Scouting mart")


@app.get("/mart/betting")
def mart_betting(limit: int = Query(default=200, ge=1, le=1000)):
    _inc("/mart/betting")
    sql = """
        SELECT
            team_id::text AS team_id,
            last5_matches,
            last5_wins,
            last5_draws,
            last5_losses,
            last5_goals_for,
            last5_goals_against
        FROM analytics.dm_betting_team_form
        ORDER BY last5_wins DESC, last5_goals_for DESC
        LIMIT :limit
    """
    return _query_mart_or_503(sql, {"limit": limit}, "Betting mart")


@app.get("/mart/content")
def mart_content(limit: int = Query(default=200, ge=1, le=1000)):
    _inc("/mart/content")
    sql = """
        SELECT
            team_id::text AS team_id,
            events_30d,
            goals_30d,
            cards_30d,
            trending_score
        FROM analytics.dm_content_team_trending
        ORDER BY trending_score DESC, goals_30d DESC
        LIMIT :limit
    """
    return _query_mart_or_503(sql, {"limit": limit}, "Content mart")


@app.get("/v1/content/trending/teams")
def v1_content_trending_teams(limit: int = Query(default=100, ge=1, le=500)):
    _inc("/v1/content/trending/teams")
    sql = """
        SELECT
            ct.team_id::text AS team_id,
            t.name AS team_name,
            ct.events_30d,
            ct.goals_30d,
            ct.cards_30d,
            ct.trending_score
        FROM analytics.dm_content_team_trending ct
        LEFT JOIN teams t ON t.id = ct.team_id
        ORDER BY ct.trending_score DESC, ct.goals_30d DESC
        LIMIT :limit
    """
    return _query_mart_or_503(sql, {"limit": limit}, "v1 content team trending")


@app.get("/v1/content/trending/players")
def v1_content_trending_players(
    team_id: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    _inc("/v1/content/trending/players")
    where_sql = ""
    params: dict[str, Any] = {"limit": limit}
    if team_id:
        where_sql = "WHERE cp.team_id = CAST(:team_id AS uuid)"
        params["team_id"] = team_id

    sql = f"""
        SELECT
            cp.player_id::text AS player_id,
            p.name AS player_name,
            cp.team_id::text AS team_id,
            t.name AS team_name,
            cp.matches_30d,
            cp.goals_30d,
            cp.assists_30d,
            cp.avg_rating_30d,
            cp.trending_score
        FROM analytics.dm_content_player_trending cp
        LEFT JOIN players p ON p.id = cp.player_id
        LEFT JOIN teams t ON t.id = cp.team_id
        {where_sql}
        ORDER BY cp.trending_score DESC, cp.goals_30d DESC, cp.assists_30d DESC
        LIMIT :limit
    """
    return _query_mart_or_503(sql, params, "v1 content player trending")


@app.get("/v1/content/matches/hot")
def v1_content_hot_matches(
    status: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    _inc("/v1/content/matches/hot")
    where_sql = ""
    params: dict[str, Any] = {"limit": limit}
    if status:
        where_sql = "WHERE mi.status = :status"
        params["status"] = status

    sql = f"""
        SELECT
            mi.match_id::text AS match_id,
            mi.kickoff_time,
            mi.status,
            mi.home_team_id::text AS home_team_id,
            ht.name AS home_team_name,
            mi.away_team_id::text AS away_team_id,
            at.name AS away_team_name,
            mi.total_events,
            mi.goals,
            mi.cards,
            mi.red_cards,
            mi.intensity_score
        FROM analytics.dm_content_match_intensity mi
        LEFT JOIN teams ht ON ht.id = mi.home_team_id
        LEFT JOIN teams at ON at.id = mi.away_team_id
        {where_sql}
        ORDER BY mi.intensity_score DESC, mi.goals DESC, mi.kickoff_time DESC NULLS LAST
        LIMIT :limit
    """
    return _query_mart_or_503(sql, params, "v1 content hot matches")


@app.get("/v1/content/stories/candidates")
def v1_content_story_candidates(limit: int = Query(default=50, ge=1, le=200)):
    _inc("/v1/content/stories/candidates")
    sql = """
        SELECT
            mi.match_id::text AS match_id,
            mi.kickoff_time,
            ht.name AS home_team_name,
            at.name AS away_team_name,
            mi.goals,
            mi.cards,
            mi.red_cards,
            mi.intensity_score,
            CASE
                WHEN mi.goals >= 5 THEN 'goal_fest'
                WHEN mi.red_cards >= 2 THEN 'discipline_flashpoint'
                WHEN mi.intensity_score >= 15 THEN 'high_intensity_battle'
                ELSE 'notable_match'
            END AS story_type
        FROM analytics.dm_content_match_intensity mi
        LEFT JOIN teams ht ON ht.id = mi.home_team_id
        LEFT JOIN teams at ON at.id = mi.away_team_id
        ORDER BY mi.intensity_score DESC, mi.kickoff_time DESC NULLS LAST
        LIMIT :limit
    """
    return _query_mart_or_503(sql, {"limit": limit}, "v1 content story candidates")


@app.get("/kpi/summary")
def kpi_summary(window_hours: int = Query(default=24, ge=1, le=168)):
    _inc("/kpi/summary")
    return collect_core_kpis(window_hours=window_hours)


@app.get("/kpi/executive")
def kpi_executive(window_hours: int = Query(default=24, ge=1, le=168)):
    _inc("/kpi/executive")
    summary = collect_core_kpis(window_hours=window_hours)
    return {
        "timestamp": summary["timestamp"],
        "window_hours": summary["window_hours"],
        "overall_status": summary["overall_status"],
        "status": summary["status"],
        "kpis": summary["kpis"],
    }


@app.post("/kpi/snapshot")
def kpi_snapshot(window_hours: int = Query(default=24, ge=1, le=168)):
    _inc("/kpi/snapshot")
    return snapshot_core_kpis(window_hours=window_hours)


@app.get("/kpi/history")
def kpi_history(
    kpi_name: Optional[str] = None,
    days: int = Query(default=30, ge=1, le=365),
):
    _inc("/kpi/history")
    start_date = date.today() - timedelta(days=days)
    with get_sync_session() as session:
        stmt = (
            select(
                KPIDailySnapshot.snapshot_date,
                KPIDailySnapshot.kpi_name,
                KPIDailySnapshot.value,
                KPIDailySnapshot.tags,
            )
            .where(KPIDailySnapshot.snapshot_date >= start_date)
        )
        if kpi_name:
            stmt = stmt.where(KPIDailySnapshot.kpi_name == kpi_name)

        stmt = stmt.order_by(KPIDailySnapshot.snapshot_date.asc(), KPIDailySnapshot.kpi_name.asc())
        rows = session.execute(stmt).mappings().all()

    return {
        "count": len(rows),
        "items": [
            {
                "snapshot_date": r["snapshot_date"].isoformat(),
                "kpi_name": r["kpi_name"],
                "value": r["value"],
                "tags": r["tags"],
            }
            for r in rows
        ],
    }


@app.get("/kpi/coverage/by-competition")
def kpi_coverage_by_competition(
    days: int = Query(default=30, ge=1, le=365),
    target_min_ratio: Optional[float] = Query(default=None, ge=0.0, le=1.0),
):
    _inc("/kpi/coverage/by-competition")
    return collect_coverage_by_competition(days=days, target_min_ratio=target_min_ratio)


@app.get("/kpi/content/coverage")
def kpi_content_coverage_by_competition(
    days: int = Query(default=30, ge=1, le=365),
    target_min_ratio: Optional[float] = Query(default=None, ge=0.0, le=1.0),
):
    _inc("/kpi/content/coverage")
    return collect_content_coverage_by_competition(days=days, target_min_ratio=target_min_ratio)


@app.post("/kpi/content/priorities/snapshot")
def kpi_content_priorities_snapshot(
    days: int = Query(default=30, ge=1, le=365),
    target_min_ratio: Optional[float] = Query(default=None, ge=0.0, le=1.0),
):
    _inc("/kpi/content/priorities/snapshot")
    return snapshot_content_priorities(days=days, target_min_ratio=target_min_ratio)


@app.get("/kpi/content/priorities/latest")
def kpi_content_priorities_latest():
    _inc("/kpi/content/priorities/latest")
    with get_sync_session() as session:
        stmt = select(ContentPriorityReport).order_by(ContentPriorityReport.report_date.desc()).limit(1)
        row = session.execute(stmt).scalars().first()

    if not row:
        return {"count": 0, "item": None}

    return {
        "count": 1,
        "item": {
            "report_date": row.report_date.isoformat(),
            "window_days": row.window_days,
            "target_min_ratio": row.target_min_ratio,
            "payload": row.payload,
            "created_at": row.created_at.isoformat(),
        },
    }


@app.get("/kpi/content/priorities/history")
def kpi_content_priorities_history(days: int = Query(default=30, ge=1, le=365)):
    _inc("/kpi/content/priorities/history")
    start_date = date.today() - timedelta(days=days)
    with get_sync_session() as session:
        stmt = (
            select(ContentPriorityReport)
            .where(ContentPriorityReport.report_date >= start_date)
            .order_by(ContentPriorityReport.report_date.desc())
        )
        rows = session.execute(stmt).scalars().all()

    return {
        "count": len(rows),
        "items": [
            {
                "report_date": r.report_date.isoformat(),
                "window_days": r.window_days,
                "target_min_ratio": r.target_min_ratio,
                "payload": r.payload,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }


@app.get("/v1/content/stories/feed")
def v1_content_stories_feed(
    days: int = Query(default=30, ge=1, le=365),
    target_min_ratio: Optional[float] = Query(default=None, ge=0.0, le=1.0),
    hot_limit: int = Query(default=5, ge=1, le=30),
    player_limit: int = Query(default=5, ge=1, le=30),
):
    _inc("/v1/content/stories/feed")
    priorities = collect_content_coverage_by_competition(days=days, target_min_ratio=target_min_ratio)

    hot_sql = """
        SELECT
            mi.match_id::text AS match_id,
            mi.kickoff_time,
            mi.status,
            ht.name AS home_team_name,
            at.name AS away_team_name,
            mi.goals,
            mi.red_cards,
            mi.intensity_score
        FROM analytics.dm_content_match_intensity mi
        LEFT JOIN teams ht ON ht.id = mi.home_team_id
        LEFT JOIN teams at ON at.id = mi.away_team_id
        ORDER BY mi.intensity_score DESC, mi.kickoff_time DESC NULLS LAST
        LIMIT :limit
    """
    player_sql = """
        SELECT
            cp.player_id::text AS player_id,
            p.name AS player_name,
            t.name AS team_name,
            cp.goals_30d,
            cp.assists_30d,
            cp.avg_rating_30d,
            cp.trending_score
        FROM analytics.dm_content_player_trending cp
        LEFT JOIN players p ON p.id = cp.player_id
        LEFT JOIN teams t ON t.id = cp.team_id
        ORDER BY cp.trending_score DESC, cp.goals_30d DESC
        LIMIT :limit
    """

    hot_matches = _query_mart_or_503(hot_sql, {"limit": hot_limit}, "hot matches")
    hot_players = _query_mart_or_503(player_sql, {"limit": player_limit}, "hot players")

    return {
        "generated_at": date.today().isoformat(),
        "coverage_overview": {
            "window_days": priorities["window_days"],
            "target_min_ratio": priorities["target_min_ratio"],
            "breach_count": priorities["breach_count"],
            "ok_count": priorities["ok_count"],
        },
        "top_actions": priorities.get("top_actions", []),
        "hot_matches": hot_matches["items"],
        "hot_players": hot_players["items"],
    }


@app.post("/admin/api-clients/create")
def admin_create_api_client(
    name: str = Query(..., min_length=2, max_length=120),
    plan: str = Query(default="free", min_length=2, max_length=30),
    rate_limit_per_minute: int = Query(default=settings.API_DEFAULT_RATE_LIMIT_PER_MINUTE, ge=1, le=100000),
):
    _inc("/admin/api-clients/create")
    raw_key = f"fi_{secrets.token_urlsafe(24)}"
    key_hash = _hash_api_key(raw_key)

    with get_sync_session() as session:
        client = APIClient(
            name=name,
            plan=plan,
            key_hash=key_hash,
            rate_limit_per_minute=rate_limit_per_minute,
            is_active=True,
        )
        session.add(client)
        session.flush()
        return {
            "id": client.id,
            "name": client.name,
            "plan": client.plan,
            "rate_limit_per_minute": client.rate_limit_per_minute,
            "api_key": raw_key,
            "warning": "Store this API key now. It is not retrievable later.",
        }


@app.get("/admin/api-clients")
def admin_list_api_clients(limit: int = Query(default=100, ge=1, le=1000)):
    _inc("/admin/api-clients")
    with get_sync_session() as session:
        stmt = select(APIClient).order_by(APIClient.created_at.desc()).limit(limit)
        rows = session.execute(stmt).scalars().all()

    return {
        "count": len(rows),
        "items": [
            {
                "id": str(r.id),
                "name": r.name,
                "plan": r.plan,
                "rate_limit_per_minute": r.rate_limit_per_minute,
                "is_active": r.is_active,
                "created_at": r.created_at.isoformat(),
                "revoked_at": _safe_iso(r.revoked_at),
            }
            for r in rows
        ],
    }


@app.post("/admin/api-clients/revoke")
def admin_revoke_api_client(client_id: uuid.UUID = Query(...)):
    _inc("/admin/api-clients/revoke")
    client_uuid = _parse_uuid(client_id, "client_id")

    with get_sync_session() as session:
        stmt = select(APIClient).where(APIClient.id == client_uuid)
        client = session.execute(stmt).scalars().first()
        if not client:
            raise HTTPException(status_code=404, detail="API client not found.")

        client.is_active = False
        client.revoked_at = datetime.utcnow()

    return {"ok": True, "id": str(client_uuid), "is_active": False}

