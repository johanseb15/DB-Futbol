# KPI Catalog (Core 2026)

This catalog defines the first production KPI set focused on business observability.

## Scope
- Window default: last 24 hours.
- Source of truth: PostgreSQL operational tables.
- API endpoints: `/kpi/summary`, `/kpi/executive`, `/kpi/history`, `/kpi/snapshot`, `/kpi/coverage/by-competition`, `/kpi/content/coverage`, `/kpi/content/priorities/*`.

## Core KPIs

### 1) `freshness_lag_seconds`
- Definition: seconds between `now()` and latest successful pipeline completion.
- SQL source: `scrape_jobs.finished_at` where `status='success'`.
- Goal: reduce lag and keep ingest current.

### 2) `quality_high_issues_total`
- Definition: count of high-severity quality findings in the window.
- SQL source: `data_quality_issues`.
- Target: `0`.

### 3) `mart_vs_raw_query_ratio`
- Definition: `mart_requests / raw_requests` for API usage events.
- SQL source: `api_request_usage` grouped by category.
- Interpretation:
  - High ratio: consumers using curated marts.
  - Null: no raw usage observed in the window.

### 4) `coverage_ratio`
- Definition: matches with both team stats and player stats divided by total matches.
- SQL source: `matches`, `match_team_stats`, `player_match_stats`.
- Goal: increase completeness for analysis-grade datasets.

### 5) `pipeline_mttr_seconds`
- Definition: mean time to recovery after failed/dead-letter runs (last 30 days).
- SQL source: `scrape_jobs` failure to next success.
- Goal: lower recovery time and minimize data downtime.

## SLA Evaluation
- Each KPI is evaluated with status:
  - `ok`
  - `breach`
  - `no_data`
- API summary includes:
  - `targets`
  - `status` per KPI
  - `overall_status` (`ok` / `degraded` / `breach`)

### Default Targets
- `freshness_lag_seconds <= 300`
- `quality_high_issues_total <= 0`
- `mart_vs_raw_query_ratio >= 1.0`
- `coverage_ratio >= 0.70`
- `pipeline_mttr_seconds <= 1800`

## Snapshot Table
- Table: `kpi_daily_snapshots`
- Uniqueness: `(snapshot_date, kpi_name)`.
- Scheduler task: `pipeline.snapshot_core_kpis` (daily).

## Notes
- This is v1 and intentionally small.
- Next version should add:
  - endpoint-level p95 latency,
  - explicit SLA status flags per KPI.

## Coverage by Competition
- Endpoint: `GET /kpi/coverage/by-competition?days=30&target_min_ratio=0.7`
- Purpose: prioritize editorial/commercial focus by league completeness.
- Output per competition:
  - `total_matches`
  - `matches_with_team_stats`
  - `matches_with_player_stats`
  - `complete_matches`
  - `coverage_ratio`
  - `status` (`ok` / `breach` / `no_data`)
  - `gap_to_target`
  - `priority_rank` for breached competitions

- Uses default window of last 30 days, configurable.
- Default target uses `KPI_COVERAGE_COMPETITION_MIN_RATIO` from settings.

## Content Pack Coverage by Competition
- Endpoint: `GET /kpi/content/coverage?days=30&target_min_ratio=0.7`
- Purpose: measure Content Pack v1 readiness per competition.
- Coverage components per competition:
  - `intensity_ratio` from `dm_content_match_intensity`
  - `team_trending_ratio` from `dm_content_team_trending`
  - `player_trending_ratio` from `dm_content_player_trending`
- Combined score:
  - `content_pack_coverage_ratio = avg(intensity_ratio, team_trending_ratio, player_trending_ratio)`
- SLA evaluation fields:
  - `status`, `gap_to_target`, `breach_severity`, `priority_rank`
- Executive guidance:
  - `top_actions` includes up to 3 prioritized recommended actions with:
    - dominant weak component (`intensity`, `team_trending`, `player_trending`)
    - operational action and data focus
    - current ratio vs target gap
- Default target uses `KPI_CONTENT_COVERAGE_COMPETITION_MIN_RATIO` from settings.

## Persisted Content Priorities
- Snapshot endpoint: `POST /kpi/content/priorities/snapshot`
- Retrieval endpoints:
  - `GET /kpi/content/priorities/latest`
  - `GET /kpi/content/priorities/history?days=30`
- Persistence table: `content_priority_reports`
- Scheduler task: `pipeline.snapshot_content_priorities` (daily).
