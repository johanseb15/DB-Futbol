"""Core KPI computation and snapshot persistence."""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import text

from config.settings import settings
from db.session import get_sync_session


CORE_KPIS = [
    "freshness_lag_seconds",
    "quality_high_issues_total",
    "mart_vs_raw_query_ratio",
    "coverage_ratio",
    "pipeline_mttr_seconds",
]


def _fetch_scalar(session, sql: str, params: dict | None = None):
    return session.execute(text(sql), params or {}).scalar_one_or_none()


def _eval_kpi_status(value: float | None, min_value: float | None = None, max_value: float | None = None) -> str:
    if value is None:
        return "no_data"
    if min_value is not None and value < min_value:
        return "breach"
    if max_value is not None and value > max_value:
        return "breach"
    return "ok"


def collect_coverage_by_competition(days: int = 30, target_min_ratio: float | None = None) -> dict:
    target = target_min_ratio if target_min_ratio is not None else settings.KPI_COVERAGE_COMPETITION_MIN_RATIO
    with get_sync_session() as session:
        rows = session.execute(
            text(
                """
                WITH base_matches AS (
                    SELECT
                        m.id AS match_id,
                        c.id AS competition_id,
                        c.name AS competition_name
                    FROM matches m
                    JOIN seasons s ON s.id = m.season_id
                    JOIN competitions c ON c.id = s.competition_id
                    WHERE m.kickoff_time >= NOW() - (:days || ' days')::interval
                ),
                aggregated AS (
                    SELECT
                        bm.competition_id,
                        bm.competition_name,
                        COUNT(*) AS total_matches,
                        SUM(
                            CASE WHEN EXISTS (
                                SELECT 1 FROM match_team_stats ts WHERE ts.match_id = bm.match_id
                            ) THEN 1 ELSE 0 END
                        ) AS matches_with_team_stats,
                        SUM(
                            CASE WHEN EXISTS (
                                SELECT 1 FROM player_match_stats ps WHERE ps.match_id = bm.match_id
                            ) THEN 1 ELSE 0 END
                        ) AS matches_with_player_stats,
                        SUM(
                            CASE WHEN EXISTS (
                                SELECT 1 FROM match_team_stats ts WHERE ts.match_id = bm.match_id
                            ) AND EXISTS (
                                SELECT 1 FROM player_match_stats ps WHERE ps.match_id = bm.match_id
                            ) THEN 1 ELSE 0 END
                        ) AS complete_matches
                    FROM base_matches bm
                    GROUP BY bm.competition_id, bm.competition_name
                )
                SELECT
                    competition_id::text AS competition_id,
                    competition_name,
                    total_matches,
                    matches_with_team_stats,
                    matches_with_player_stats,
                    complete_matches,
                    CASE WHEN total_matches = 0 THEN NULL
                         ELSE complete_matches::float / total_matches::float
                    END AS coverage_ratio
                FROM aggregated
                ORDER BY coverage_ratio DESC NULLS LAST, total_matches DESC
                """
            ),
            {"days": days},
        ).mappings().all()

    items = []
    for row in rows:
        item = dict(row)
        coverage = item.get("coverage_ratio")
        status = _eval_kpi_status(coverage, min_value=target)
        if coverage is None:
            gap = None
            breach_severity = 0.0
        else:
            gap = round(target - float(coverage), 6)
            breach_severity = max(0.0, gap)

        item["target_min_ratio"] = target
        item["status"] = status
        item["gap_to_target"] = gap
        item["breach_severity"] = breach_severity
        items.append(item)

    prioritized = sorted(
        items,
        key=lambda x: (x["status"] != "breach", -x["breach_severity"], -int(x["total_matches"] or 0)),
    )
    for idx, item in enumerate(prioritized, start=1):
        item["priority_rank"] = idx if item["status"] == "breach" else None

    breach_count = sum(1 for i in items if i["status"] == "breach")
    ok_count = sum(1 for i in items if i["status"] == "ok")
    no_data_count = sum(1 for i in items if i["status"] == "no_data")
    return {
        "window_days": days,
        "target_min_ratio": target,
        "count": len(prioritized),
        "breach_count": breach_count,
        "ok_count": ok_count,
        "no_data_count": no_data_count,
        "items": prioritized,
    }


def collect_content_coverage_by_competition(days: int = 30, target_min_ratio: float | None = None) -> dict:
    target = (
        target_min_ratio
        if target_min_ratio is not None
        else settings.KPI_CONTENT_COVERAGE_COMPETITION_MIN_RATIO
    )
    with get_sync_session() as session:
        rows = session.execute(
            text(
                """
                WITH base_matches AS (
                    SELECT
                        m.id AS match_id,
                        c.id AS competition_id,
                        c.name AS competition_name,
                        m.home_team_id,
                        m.away_team_id
                    FROM matches m
                    JOIN seasons s ON s.id = m.season_id
                    JOIN competitions c ON c.id = s.competition_id
                    WHERE m.kickoff_time >= NOW() - (:days || ' days')::interval
                ),
                match_level AS (
                    SELECT
                        bm.competition_id,
                        bm.competition_name,
                        bm.match_id,
                        CASE WHEN mi.match_id IS NOT NULL THEN 1 ELSE 0 END AS has_intensity,
                        CASE WHEN t1.team_id IS NOT NULL AND t2.team_id IS NOT NULL THEN 1 ELSE 0 END AS has_team_trending
                    FROM base_matches bm
                    LEFT JOIN analytics.dm_content_match_intensity mi ON mi.match_id = bm.match_id
                    LEFT JOIN analytics.dm_content_team_trending t1 ON t1.team_id = bm.home_team_id
                    LEFT JOIN analytics.dm_content_team_trending t2 ON t2.team_id = bm.away_team_id
                ),
                player_level AS (
                    SELECT
                        bm.competition_id,
                        bm.competition_name,
                        bm.match_id,
                        CASE WHEN COUNT(cp.player_id) > 0 THEN 1 ELSE 0 END AS has_player_trending
                    FROM base_matches bm
                    LEFT JOIN player_match_stats pms ON pms.match_id = bm.match_id
                    LEFT JOIN analytics.dm_content_player_trending cp ON cp.player_id = pms.player_id
                    GROUP BY bm.competition_id, bm.competition_name, bm.match_id
                ),
                aggregated AS (
                    SELECT
                        ml.competition_id,
                        ml.competition_name,
                        COUNT(*) AS total_matches,
                        SUM(ml.has_intensity) AS matches_with_intensity,
                        SUM(ml.has_team_trending) AS matches_with_team_trending,
                        SUM(pl.has_player_trending) AS matches_with_player_trending
                    FROM match_level ml
                    JOIN player_level pl
                      ON pl.competition_id = ml.competition_id
                     AND pl.match_id = ml.match_id
                    GROUP BY ml.competition_id, ml.competition_name
                )
                SELECT
                    competition_id::text AS competition_id,
                    competition_name,
                    total_matches,
                    matches_with_intensity,
                    matches_with_team_trending,
                    matches_with_player_trending,
                    CASE WHEN total_matches = 0 THEN NULL
                         ELSE matches_with_intensity::float / total_matches::float
                    END AS intensity_ratio,
                    CASE WHEN total_matches = 0 THEN NULL
                         ELSE matches_with_team_trending::float / total_matches::float
                    END AS team_trending_ratio,
                    CASE WHEN total_matches = 0 THEN NULL
                         ELSE matches_with_player_trending::float / total_matches::float
                    END AS player_trending_ratio,
                    CASE WHEN total_matches = 0 THEN NULL
                         ELSE (
                           (matches_with_intensity::float / total_matches::float) +
                           (matches_with_team_trending::float / total_matches::float) +
                           (matches_with_player_trending::float / total_matches::float)
                         ) / 3.0
                    END AS content_pack_coverage_ratio
                FROM aggregated
                ORDER BY content_pack_coverage_ratio DESC NULLS LAST, total_matches DESC
                """
            ),
            {"days": days},
        ).mappings().all()

    items = []
    for row in rows:
        item = dict(row)
        ratio = item.get("content_pack_coverage_ratio")
        intensity_ratio = item.get("intensity_ratio")
        team_ratio = item.get("team_trending_ratio")
        player_ratio = item.get("player_trending_ratio")

        intensity_gap = None if intensity_ratio is None else max(0.0, target - float(intensity_ratio))
        team_gap = None if team_ratio is None else max(0.0, target - float(team_ratio))
        player_gap = None if player_ratio is None else max(0.0, target - float(player_ratio))

        gap_components = {
            "intensity": intensity_gap if intensity_gap is not None else 0.0,
            "team_trending": team_gap if team_gap is not None else 0.0,
            "player_trending": player_gap if player_gap is not None else 0.0,
        }
        dominant_gap_component = max(gap_components, key=gap_components.get)

        status = _eval_kpi_status(ratio, min_value=target)
        if ratio is None:
            gap = None
            breach_severity = 0.0
        else:
            gap = round(target - float(ratio), 6)
            breach_severity = max(0.0, gap)

        item["target_min_ratio"] = target
        item["status"] = status
        item["gap_to_target"] = gap
        item["breach_severity"] = breach_severity
        item["intensity_gap_to_target"] = intensity_gap
        item["team_trending_gap_to_target"] = team_gap
        item["player_trending_gap_to_target"] = player_gap
        item["dominant_gap_component"] = dominant_gap_component
        items.append(item)

    prioritized = sorted(
        items,
        key=lambda x: (x["status"] != "breach", -x["breach_severity"], -int(x["total_matches"] or 0)),
    )
    for idx, item in enumerate(prioritized, start=1):
        item["priority_rank"] = idx if item["status"] == "breach" else None

    breach_count = sum(1 for i in items if i["status"] == "breach")
    ok_count = sum(1 for i in items if i["status"] == "ok")
    no_data_count = sum(1 for i in items if i["status"] == "no_data")

    recommendations = []
    for item in prioritized:
        if item["status"] != "breach":
            continue

        component = item["dominant_gap_component"]
        if component == "intensity":
            action = "Priorizar normalizacion de eventos de partido y refresh de dm_content_match_intensity."
            data_focus = "match_events + matches"
        elif component == "team_trending":
            action = "Priorizar cobertura de eventos por equipo para robustecer dm_content_team_trending."
            data_focus = "match_events(team_id)"
        else:
            action = "Priorizar enrichment de player_match_stats para elevar dm_content_player_trending."
            data_focus = "player_match_stats + player mapping"

        recommendations.append(
            {
                "competition_id": item["competition_id"],
                "competition_name": item["competition_name"],
                "priority_rank": item["priority_rank"],
                "dominant_gap_component": component,
                "action": action,
                "data_focus": data_focus,
                "current_ratio": item["content_pack_coverage_ratio"],
                "target_ratio": target,
                "gap_to_target": item["gap_to_target"],
            }
        )
        if len(recommendations) == 3:
            break

    return {
        "window_days": days,
        "target_min_ratio": target,
        "count": len(prioritized),
        "breach_count": breach_count,
        "ok_count": ok_count,
        "no_data_count": no_data_count,
        "items": prioritized,
        "top_actions": recommendations,
    }


def collect_core_kpis(window_hours: int = 24) -> dict:
    now = datetime.now(timezone.utc)
    with get_sync_session() as session:
        latest_success_at = _fetch_scalar(
            session,
            """
            SELECT MAX(finished_at)
            FROM scrape_jobs
            WHERE status = 'success' AND finished_at IS NOT NULL
            """,
        )
        if latest_success_at is None:
            freshness = None
        else:
            freshness = max(0.0, (now - latest_success_at).total_seconds())

        quality_high = int(
            _fetch_scalar(
                session,
                """
                SELECT COUNT(*)
                FROM data_quality_issues
                WHERE severity = 'high'
                  AND detected_at >= NOW() - (:window_hours || ' hours')::interval
                """,
                {"window_hours": window_hours},
            )
            or 0
        )

        mart_queries = int(
            _fetch_scalar(
                session,
                """
                SELECT COUNT(*)
                FROM api_request_usage
                WHERE category = 'mart'
                  AND requested_at >= NOW() - (:window_hours || ' hours')::interval
                """,
                {"window_hours": window_hours},
            )
            or 0
        )
        raw_queries = int(
            _fetch_scalar(
                session,
                """
                SELECT COUNT(*)
                FROM api_request_usage
                WHERE category = 'raw'
                  AND requested_at >= NOW() - (:window_hours || ' hours')::interval
                """,
                {"window_hours": window_hours},
            )
            or 0
        )
        mart_vs_raw = None if raw_queries == 0 else (mart_queries / raw_queries)

        total_matches = int(
            _fetch_scalar(
                session,
                """
                SELECT COUNT(*) FROM matches
                WHERE kickoff_time IS NOT NULL
                """,
            )
            or 0
        )
        complete_matches = int(
            _fetch_scalar(
                session,
                """
                SELECT COUNT(*)
                FROM matches m
                WHERE EXISTS (SELECT 1 FROM match_team_stats ts WHERE ts.match_id = m.id)
                  AND EXISTS (SELECT 1 FROM player_match_stats ps WHERE ps.match_id = m.id)
                """,
            )
            or 0
        )
        coverage_ratio = (complete_matches / total_matches) if total_matches > 0 else None

        mttr = _fetch_scalar(
            session,
            """
            WITH failed_jobs AS (
                SELECT id, started_at
                FROM scrape_jobs
                WHERE status IN ('failed', 'dead_letter')
                  AND started_at IS NOT NULL
                  AND started_at >= NOW() - INTERVAL '30 days'
            ),
            recoveries AS (
                SELECT
                    f.id AS failed_job_id,
                    MIN(s.started_at) AS recovered_at,
                    f.started_at AS failed_at
                FROM failed_jobs f
                JOIN scrape_jobs s
                  ON s.status = 'success'
                 AND s.started_at > f.started_at
                GROUP BY f.id, f.started_at
            )
            SELECT AVG(EXTRACT(EPOCH FROM (recovered_at - failed_at)))
            FROM recoveries
            """,
        )
        mttr_seconds = float(mttr) if mttr is not None else None

    kpis = {
        "freshness_lag_seconds": freshness,
        "quality_high_issues_total": float(quality_high),
        "mart_vs_raw_query_ratio": mart_vs_raw,
        "coverage_ratio": coverage_ratio,
        "pipeline_mttr_seconds": mttr_seconds,
    }
    targets = {
        "freshness_lag_seconds": {"max": settings.KPI_FRESHNESS_MAX_SECONDS},
        "quality_high_issues_total": {"max": settings.KPI_QUALITY_HIGH_MAX},
        "mart_vs_raw_query_ratio": {"min": settings.KPI_MART_RAW_MIN_RATIO},
        "coverage_ratio": {"min": settings.KPI_COVERAGE_MIN_RATIO},
        "pipeline_mttr_seconds": {"max": settings.KPI_MTTR_MAX_SECONDS},
    }
    status = {
        "freshness_lag_seconds": _eval_kpi_status(
            kpis["freshness_lag_seconds"],
            max_value=settings.KPI_FRESHNESS_MAX_SECONDS,
        ),
        "quality_high_issues_total": _eval_kpi_status(
            kpis["quality_high_issues_total"],
            max_value=settings.KPI_QUALITY_HIGH_MAX,
        ),
        "mart_vs_raw_query_ratio": _eval_kpi_status(
            kpis["mart_vs_raw_query_ratio"],
            min_value=settings.KPI_MART_RAW_MIN_RATIO,
        ),
        "coverage_ratio": _eval_kpi_status(
            kpis["coverage_ratio"],
            min_value=settings.KPI_COVERAGE_MIN_RATIO,
        ),
        "pipeline_mttr_seconds": _eval_kpi_status(
            kpis["pipeline_mttr_seconds"],
            max_value=settings.KPI_MTTR_MAX_SECONDS,
        ),
    }

    breach_count = sum(1 for v in status.values() if v == "breach")
    no_data_count = sum(1 for v in status.values() if v == "no_data")
    overall = "breach" if breach_count > 0 else ("degraded" if no_data_count > 0 else "ok")

    return {
        "timestamp": now.isoformat(),
        "window_hours": window_hours,
        "kpis": kpis,
        "targets": targets,
        "status": status,
        "overall_status": overall,
        "diagnostics": {
            "mart_queries_window": mart_queries,
            "raw_queries_window": raw_queries,
            "total_matches": total_matches,
            "complete_matches": complete_matches,
        },
    }


def snapshot_core_kpis(window_hours: int = 24) -> dict:
    summary = collect_core_kpis(window_hours=window_hours)
    today = date.today()
    values = summary["kpis"]
    status = summary["status"]
    targets = summary["targets"]
    with get_sync_session() as session:
        for kpi_name, kpi_value in values.items():
            session.execute(
                text(
                    """
                    INSERT INTO kpi_daily_snapshots (id, snapshot_date, kpi_name, value, tags)
                    VALUES (:id, :snapshot_date, :kpi_name, :value, CAST(:tags AS jsonb))
                    ON CONFLICT (snapshot_date, kpi_name)
                    DO UPDATE SET value = EXCLUDED.value, tags = EXCLUDED.tags
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "snapshot_date": today.isoformat(),
                    "kpi_name": kpi_name,
                    "value": kpi_value,
                    "tags": (
                        '{"window_hours": %d, "status": "%s", "targets": %s}'
                        % (window_hours, status[kpi_name], str(targets[kpi_name]).replace("'", '"'))
                    ),
                },
            )
    return summary


def snapshot_content_priorities(days: int = 30, target_min_ratio: float | None = None) -> dict:
    report = collect_content_coverage_by_competition(days=days, target_min_ratio=target_min_ratio)
    payload_json = json.dumps(report, ensure_ascii=True)
    with get_sync_session() as session:
        session.execute(
            text(
                """
                INSERT INTO content_priority_reports (id, report_date, window_days, target_min_ratio, payload)
                VALUES (:id, CURRENT_DATE, :window_days, :target_min_ratio, CAST(:payload AS jsonb))
                ON CONFLICT (report_date)
                DO UPDATE SET
                    window_days = EXCLUDED.window_days,
                    target_min_ratio = EXCLUDED.target_min_ratio,
                    payload = EXCLUDED.payload
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "window_days": days,
                "target_min_ratio": report["target_min_ratio"],
                "payload": payload_json,
            },
        )
    return report

