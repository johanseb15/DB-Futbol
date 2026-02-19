-- Data marts for business use cases: scouting, betting, content.

CREATE SCHEMA IF NOT EXISTS analytics;

-- 1) Scouting: player aggregates by season/team.
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.dm_scouting_player_season AS
SELECT
    m.season_id,
    pms.player_id,
    pms.team_id,
    COUNT(*) AS matches,
    SUM(COALESCE(pms.minutes_played, 0)) AS minutes_played,
    SUM(COALESCE(pms.goals, 0)) AS goals,
    SUM(COALESCE(pms.assists, 0)) AS assists,
    ROUND(AVG(COALESCE(pms.rating, 0))::numeric, 2) AS avg_rating,
    SUM(COALESCE(pms.shots, 0)) AS shots
FROM player_match_stats pms
JOIN matches m ON m.id = pms.match_id
GROUP BY m.season_id, pms.player_id, pms.team_id;

CREATE INDEX IF NOT EXISTS ix_dm_scouting_player_season
ON analytics.dm_scouting_player_season (season_id, player_id, team_id);

-- 2) Betting: team form over recent finished matches.
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.dm_betting_team_form AS
WITH team_matches AS (
    SELECT
        m.id AS match_id,
        m.kickoff_time,
        m.status,
        m.season_id,
        m.home_team_id AS team_id,
        m.away_team_id AS opponent_team_id,
        m.home_score AS goals_for,
        m.away_score AS goals_against
    FROM matches m
    UNION ALL
    SELECT
        m.id AS match_id,
        m.kickoff_time,
        m.status,
        m.season_id,
        m.away_team_id AS team_id,
        m.home_team_id AS opponent_team_id,
        m.away_score AS goals_for,
        m.home_score AS goals_against
    FROM matches m
),
ranked AS (
    SELECT
        tm.*,
        ROW_NUMBER() OVER (PARTITION BY tm.team_id ORDER BY tm.kickoff_time DESC NULLS LAST) AS rn
    FROM team_matches tm
    WHERE tm.status = 'finished'
)
SELECT
    team_id,
    COUNT(*) FILTER (WHERE rn <= 5) AS last5_matches,
    SUM(CASE WHEN rn <= 5 AND goals_for > goals_against THEN 1 ELSE 0 END) AS last5_wins,
    SUM(CASE WHEN rn <= 5 AND goals_for = goals_against THEN 1 ELSE 0 END) AS last5_draws,
    SUM(CASE WHEN rn <= 5 AND goals_for < goals_against THEN 1 ELSE 0 END) AS last5_losses,
    SUM(CASE WHEN rn <= 5 THEN COALESCE(goals_for, 0) ELSE 0 END) AS last5_goals_for,
    SUM(CASE WHEN rn <= 5 THEN COALESCE(goals_against, 0) ELSE 0 END) AS last5_goals_against
FROM ranked
GROUP BY team_id;

CREATE INDEX IF NOT EXISTS ix_dm_betting_team_form_team
ON analytics.dm_betting_team_form (team_id);

-- 3) Content: team engagement proxy from goals/events in recent window.
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.dm_content_team_trending AS
WITH recent_matches AS (
    SELECT id, home_team_id, away_team_id, kickoff_time
    FROM matches
    WHERE kickoff_time >= NOW() - INTERVAL '30 days'
),
team_events AS (
    SELECT
        me.team_id,
        COUNT(*) AS events_30d,
        SUM(CASE WHEN me.type IN ('goal', 'own_goal', 'penalty_goal') THEN 1 ELSE 0 END) AS goals_30d,
        SUM(CASE WHEN me.type IN ('yellow_card', 'red_card', 'yellow_red_card') THEN 1 ELSE 0 END) AS cards_30d
    FROM match_events me
    JOIN recent_matches rm ON rm.id = me.match_id
    GROUP BY me.team_id
)
SELECT
    te.team_id,
    te.events_30d,
    te.goals_30d,
    te.cards_30d,
    (te.goals_30d * 3 + te.events_30d) AS trending_score
FROM team_events te;

CREATE INDEX IF NOT EXISTS ix_dm_content_team_trending_team
ON analytics.dm_content_team_trending (team_id);

-- 4) Content: player trending over recent window for editorial/storytelling.
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.dm_content_player_trending AS
WITH recent_matches AS (
    SELECT id
    FROM matches
    WHERE kickoff_time >= NOW() - INTERVAL '30 days'
),
recent_player_stats AS (
    SELECT
        pms.player_id,
        pms.team_id,
        COUNT(*) AS matches_30d,
        SUM(COALESCE(pms.goals, 0)) AS goals_30d,
        SUM(COALESCE(pms.assists, 0)) AS assists_30d,
        ROUND(AVG(COALESCE(pms.rating, 0))::numeric, 2) AS avg_rating_30d
    FROM player_match_stats pms
    JOIN recent_matches rm ON rm.id = pms.match_id
    GROUP BY pms.player_id, pms.team_id
),
recent_player_events AS (
    SELECT
        me.player_id,
        SUM(CASE WHEN me.type IN ('goal', 'own_goal', 'penalty_goal') THEN 1 ELSE 0 END) AS goal_events_30d,
        SUM(CASE WHEN me.type IN ('yellow_card', 'red_card', 'yellow_red_card') THEN 1 ELSE 0 END) AS cards_30d
    FROM match_events me
    JOIN recent_matches rm ON rm.id = me.match_id
    WHERE me.player_id IS NOT NULL
    GROUP BY me.player_id
)
SELECT
    rps.player_id,
    rps.team_id,
    rps.matches_30d,
    rps.goals_30d,
    rps.assists_30d,
    rps.avg_rating_30d,
    COALESCE(rpe.goal_events_30d, 0) AS goal_events_30d,
    COALESCE(rpe.cards_30d, 0) AS cards_30d,
    (COALESCE(rps.goals_30d, 0) * 4 + COALESCE(rps.assists_30d, 0) * 3 + COALESCE(rps.avg_rating_30d, 0)) AS trending_score
FROM recent_player_stats rps
LEFT JOIN recent_player_events rpe ON rpe.player_id = rps.player_id;

CREATE INDEX IF NOT EXISTS ix_dm_content_player_trending_player
ON analytics.dm_content_player_trending (player_id);

CREATE INDEX IF NOT EXISTS ix_dm_content_player_trending_team
ON analytics.dm_content_player_trending (team_id);

-- 5) Content: match intensity for hot-match and narrative ranking.
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.dm_content_match_intensity AS
WITH event_counts AS (
    SELECT
        me.match_id,
        COUNT(*) AS total_events,
        SUM(CASE WHEN me.type IN ('goal', 'own_goal', 'penalty_goal') THEN 1 ELSE 0 END) AS goals,
        SUM(CASE WHEN me.type IN ('yellow_card', 'red_card', 'yellow_red_card') THEN 1 ELSE 0 END) AS cards,
        SUM(CASE WHEN me.type IN ('red_card', 'yellow_red_card') THEN 1 ELSE 0 END) AS red_cards
    FROM match_events me
    GROUP BY me.match_id
)
SELECT
    m.id AS match_id,
    m.season_id,
    m.kickoff_time,
    m.status,
    m.home_team_id,
    m.away_team_id,
    COALESCE(ec.total_events, 0) AS total_events,
    COALESCE(ec.goals, 0) AS goals,
    COALESCE(ec.cards, 0) AS cards,
    COALESCE(ec.red_cards, 0) AS red_cards,
    (COALESCE(ec.goals, 0) * 5 + COALESCE(ec.red_cards, 0) * 3 + COALESCE(ec.cards, 0) + COALESCE(ec.total_events, 0) * 0.2) AS intensity_score
FROM matches m
LEFT JOIN event_counts ec ON ec.match_id = m.id
WHERE m.kickoff_time >= NOW() - INTERVAL '30 days';

CREATE INDEX IF NOT EXISTS ix_dm_content_match_intensity_match
ON analytics.dm_content_match_intensity (match_id);

CREATE INDEX IF NOT EXISTS ix_dm_content_match_intensity_score
ON analytics.dm_content_match_intensity (intensity_score);
