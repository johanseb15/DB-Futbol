"""Data quality checks for critical pipeline entities."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import text

from db.session import get_sync_session


def run_data_quality_checks() -> dict:
    run_id = uuid.uuid4()
    checked_at = datetime.now(timezone.utc)

    checks = [
        {
            "check_name": "duplicate_players_by_sofascore_id",
            "severity": "high",
            "entity_type": "players",
            "query": """
                SELECT CAST(sofascore_id AS TEXT) AS entity_id, COUNT(*) AS issue_count
                FROM players
                WHERE sofascore_id IS NOT NULL
                GROUP BY sofascore_id
                HAVING COUNT(*) > 1
            """,
            "message": "Duplicate players found by sofascore_id.",
        },
        {
            "check_name": "duplicate_teams_by_sofascore_id",
            "severity": "high",
            "entity_type": "teams",
            "query": """
                SELECT CAST(sofascore_id AS TEXT) AS entity_id, COUNT(*) AS issue_count
                FROM teams
                WHERE sofascore_id IS NOT NULL
                GROUP BY sofascore_id
                HAVING COUNT(*) > 1
            """,
            "message": "Duplicate teams found by sofascore_id.",
        },
        {
            "check_name": "matches_missing_critical_fields",
            "severity": "high",
            "entity_type": "matches",
            "query": """
                SELECT CAST(id AS TEXT) AS entity_id, 1 AS issue_count
                FROM matches
                WHERE season_id IS NULL
                   OR home_team_id IS NULL
                   OR away_team_id IS NULL
                   OR status IS NULL
            """,
            "message": "Match is missing at least one critical field.",
        },
        {
            "check_name": "finished_matches_without_score",
            "severity": "medium",
            "entity_type": "matches",
            "query": """
                SELECT CAST(id AS TEXT) AS entity_id, 1 AS issue_count
                FROM matches
                WHERE status = 'finished'
                  AND (home_score IS NULL OR away_score IS NULL)
            """,
            "message": "Finished match has null score fields.",
        },
        {
            "check_name": "scheduled_with_scores",
            "severity": "low",
            "entity_type": "matches",
            "query": """
                SELECT CAST(id AS TEXT) AS entity_id, 1 AS issue_count
                FROM matches
                WHERE status IN ('scheduled', 'postponed', 'cancelled')
                  AND (home_score IS NOT NULL OR away_score IS NOT NULL)
            """,
            "message": "Non-played match has score values.",
        },
    ]

    created = 0
    by_check: dict[str, int] = {}

    with get_sync_session() as session:
        session.execute(text("DELETE FROM data_quality_issues WHERE detected_at >= NOW() - INTERVAL '36 hours'"))

        for check in checks:
            rows = session.execute(text(check["query"])).mappings().all()
            by_check[check["check_name"]] = len(rows)
            for row in rows:
                session.execute(
                    text(
                        """
                        INSERT INTO data_quality_issues (
                            id, check_name, severity, source, competition_key, entity_type,
                            entity_id, issue_count, sample, message, detected_at, run_id
                        ) VALUES (
                            :id, :check_name, :severity, :source, :competition_key, :entity_type,
                            :entity_id, :issue_count, CAST(:sample AS jsonb), :message, :detected_at, :run_id
                        )
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "check_name": check["check_name"],
                        "severity": check["severity"],
                        "source": None,
                        "competition_key": None,
                        "entity_type": check["entity_type"],
                        "entity_id": row.get("entity_id"),
                        "issue_count": int(row.get("issue_count") or 1),
                        "sample": "{}",
                        "message": check["message"],
                        "detected_at": checked_at,
                        "run_id": str(run_id),
                    },
                )
                created += 1

    return {
        "run_id": str(run_id),
        "detected_at": checked_at.isoformat(),
        "issues_created": created,
        "checks": by_check,
    }

