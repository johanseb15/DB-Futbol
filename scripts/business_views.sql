-- Business-facing analytics views.

CREATE SCHEMA IF NOT EXISTS analytics;

CREATE OR REPLACE VIEW analytics.vw_team_season_performance AS
WITH team_matches AS (
    SELECT
        m.id AS match_id,
        m.season_id,
        m.home_team_id AS team_id,
        m.away_team_id AS opponent_team_id,
        m.home_score AS goals_for,
        m.away_score AS goals_against,
        m.kickoff_time,
        m.status
    FROM matches m
    UNION ALL
    SELECT
        m.id AS match_id,
        m.season_id,
        m.away_team_id AS team_id,
        m.home_team_id AS opponent_team_id,
        m.away_score AS goals_for,
        m.home_score AS goals_against,
        m.kickoff_time,
        m.status
    FROM matches m
)
SELECT
    tm.season_id,
    tm.team_id,
    COUNT(*) FILTER (WHERE tm.status = 'finished') AS matches_finished,
    SUM(CASE WHEN tm.status = 'finished' AND tm.goals_for > tm.goals_against THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN tm.status = 'finished' AND tm.goals_for = tm.goals_against THEN 1 ELSE 0 END) AS draws,
    SUM(CASE WHEN tm.status = 'finished' AND tm.goals_for < tm.goals_against THEN 1 ELSE 0 END) AS losses,
    SUM(CASE WHEN tm.status = 'finished' THEN COALESCE(tm.goals_for, 0) ELSE 0 END) AS goals_for,
    SUM(CASE WHEN tm.status = 'finished' THEN COALESCE(tm.goals_against, 0) ELSE 0 END) AS goals_against,
    SUM(
        CASE
            WHEN tm.status = 'finished' AND tm.goals_for > tm.goals_against THEN 3
            WHEN tm.status = 'finished' AND tm.goals_for = tm.goals_against THEN 1
            ELSE 0
        END
    ) AS points
FROM team_matches tm
GROUP BY tm.season_id, tm.team_id;

CREATE OR REPLACE VIEW analytics.vw_player_value_trend AS
SELECT
    mv.player_id,
    mv.team_id,
    mv.recorded_at,
    mv.value_eur,
    LAG(mv.value_eur) OVER (PARTITION BY mv.player_id ORDER BY mv.recorded_at) AS prev_value_eur,
    CASE
        WHEN LAG(mv.value_eur) OVER (PARTITION BY mv.player_id ORDER BY mv.recorded_at) IS NULL THEN NULL
        ELSE mv.value_eur - LAG(mv.value_eur) OVER (PARTITION BY mv.player_id ORDER BY mv.recorded_at)
    END AS delta_value_eur
FROM market_values mv;

