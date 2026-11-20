> **Ficha de proyecto — Vyntrava | 2026-11-20**
> Estado documental: revisión de repositorio; no implica despliegue ni auditoría de producción.

## Resumen y propósito

**Laboratorio de datos deportivos.** Pipeline Python para capturar, normalizar y almacenar información futbolística en PostgreSQL; estructura de scrapers, migraciones, API y pruebas.

## Estado y límites

Código experimental con dependencias de fuentes externas. No se verificó la vigencia, autorización ni funcionamiento actual de cada scraper.

## Ubicación en el portfolio

Referencia de ingeniería de datos y normalización, no una fuente comercial de datos deportivos certificada.

**Código:** [DB-Futbol](https://github.com/johanseb15/DB-Futbol) · **Documentación técnica original:** continúa a continuación y puede reflejar un estado histórico.

---

# Football Intelligence DB

Backend de datos de fútbol: scraping + normalización + PostgreSQL.  
Cubre Argentina (todas las categorías) + Top 5 ligas europeas + UCL.

---

## Arquitectura

```text
┌─────────────────────────────────────────────────────────────┐
│  SOURCES                                                    │
│  Sofascore (API JSON)  ──┐                                  │
│  Transfermarkt (HTML)  ──┼──► scrapers/   ──► scrape_raw   │
│  API-Football (REST)   ──┘                     (staging)   │
└─────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────┐
│  PIPELINE                                                   │
│  pipeline/normalizer.py  ──► clean tables (PostgreSQL)     │
│  - Teams, Players, Coaches                                  │
│  - Matches, Events, Stats                                   │
│  - MarketValues, Transfers                                  │
└─────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────┐
│  STORAGE (PostgreSQL)                                       │
│  15 clean tables + 2 staging tables                         │
│  Full audit trail via scrape_raw                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Setup - Paso a Paso

### 1. Pre-requisitos

```bash
# Python 3.13 recomendado en Windows
py -0p

# Docker + Docker Compose
docker --version
docker compose version
```

### 2. Crear entorno e instalar

```bash
# Windows (recomendado)
py -3.13 -m venv venv313
venv313\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Instalar Playwright browsers (para scraping de páginas JS)
python -m playwright install chromium
```

### 3. Configurar variables de entorno

```bash
# Este repo ya trae .env listo.
# Editalo si necesitás cambiar credenciales/hosts.
```

### 4. Levantar PostgreSQL y Redis

```bash
docker compose up -d
```

Verificar que estén corriendo:

```bash
docker compose ps
# Deberías ver football_db (healthy) y football_redis (up)
```

### 5. Inicializar la base de datos

```bash
# Crear tablas
python -m pipeline.runner --init-db

# Cargar datos de referencia (países + competencias)
python scripts/seed.py
```

### 6. Primer scraping

```bash
# Descubrir seasons disponibles para una competencia
python -m pipeline.runner --discover arg_liga_profesional

# Scraping de Liga Profesional Argentina (season ejemplo)
python -m pipeline.runner --competition arg_liga_profesional --season 62063

# Scraping de Premier League
python -m pipeline.runner --competition eng_premier_league --season 61643

# Todas las competencias (puede tardar varias horas)
python -m pipeline.runner --all
```

Nota: Sofascore puede responder `403 Forbidden` por anti-bot según IP/rate-limit.  
En ese caso el pipeline corre, pero puede guardar 0 matches en esa ejecución.

---

## Estructura del Proyecto

```text
football-db/
├── config/
│   └── settings.py           # Variables de entorno centralizadas
├── db/
│   ├── models/
│   │   ├── base.py           # UUIDMixin, TimestampMixin
│   │   ├── geography.py      # Country, Competition, Season, Venue
│   │   ├── people.py         # Player, Coach, Referee
│   │   ├── teams.py          # Team, TeamSeason, PlayerContract
│   │   ├── matches.py        # Match, MatchEvent, MatchTeamStats, PlayerMatchStats
│   │   ├── transfers.py      # MarketValue, Transfer
│   │   └── staging.py        # ScrapeJob, ScrapeRaw
│   └── session.py            # Engine, session factory
├── scrapers/
│   ├── base.py               # BaseScraper: rate limiting, retry, cache
│   ├── sofascore/
│   │   └── scraper.py        # API JSON de Sofascore
│   └── transfermarkt/
│       └── scraper.py        # HTML scraper Transfermarkt
├── pipeline/
│   ├── normalizer.py         # Raw -> clean tables
│   └── runner.py             # CLI orquestador
├── scripts/
│   ├── init.sql              # PG extensions
│   └── seed.py               # Datos de referencia
├── docker-compose.yml
├── requirements.txt
└── .env
```

---

## Schema de Base de Datos

### Tablas Principales (15)

| Tabla | Descripción | Filas estimadas |
|-------|-------------|-----------------|
| `countries` | Referencia geográfica | ~50 |
| `competitions` | Ligas, copas, torneos | ~10 |
| `seasons` | Edición por año de cada competencia | ~50 |
| `venues` | Estadios | ~500 |
| `teams` | Clubes y selecciones | ~500 |
| `team_seasons` | Participación equipo × temporada | ~1,000 |
| `players` | Jugadores | ~50,000 |
| `player_contracts` | Historial contractual | ~100,000 |
| `coaches` | Técnicos | ~500 |
| `referees` | Árbitros | ~1,000 |
| `matches` | Partidos | ~50,000 |
| `match_events` | Goles, tarjetas, cambios | ~500,000 |
| `match_team_stats` | Stats agregadas por equipo por partido | ~100,000 |
| `player_match_stats` | Stats individuales por jugador por partido | ~1,000,000 |
| `market_values` | Historial de valores de mercado | ~500,000 |
| `transfers` | Transferencias | ~200,000 |

### Tablas de Staging (2)

| Tabla | Descripción |
|-------|-------------|
| `scrape_jobs` | Log de ejecuciones del scraper |
| `scrape_raw` | Payloads JSON crudos sin transformar |

---

## Queries Útiles

```sql
-- Top 10 jugadores argentinos por valor de mercado actual
SELECT p.name, mv.value_eur, t.name AS club
FROM players p
JOIN market_values mv ON mv.player_id = p.id
JOIN player_contracts pc ON pc.player_id = p.id AND pc.is_current = true
JOIN teams t ON t.id = pc.team_id
JOIN countries c ON c.id = p.nationality_id
WHERE c.code_iso2 = 'AR'
ORDER BY mv.value_eur DESC NULLS LAST
LIMIT 10;

-- Partidos de la Liga Profesional con goles
SELECT m.kickoff_time,
       ht.name AS home, m.home_score,
       at.name AS away, m.away_score
FROM matches m
JOIN teams ht ON ht.id = m.home_team_id
JOIN teams at ON at.id = m.away_team_id
JOIN seasons s ON s.id = m.season_id
JOIN competitions c ON c.id = s.competition_id
WHERE c.sofascore_id = 155
  AND m.status = 'finished'
ORDER BY m.kickoff_time DESC
LIMIT 20;

-- Máximos goleadores de una temporada
SELECT p.name, t.name AS team, SUM(pms.goals) AS total_goals
FROM player_match_stats pms
JOIN players p ON p.id = pms.player_id
JOIN teams t ON t.id = pms.team_id
JOIN matches m ON m.id = pms.match_id
JOIN seasons s ON s.id = m.season_id
WHERE s.sofascore_id = 62063
GROUP BY p.name, t.name
ORDER BY total_goals DESC
LIMIT 20;

-- Árbitros con más tarjetas en promedio
SELECT r.name,
       COUNT(DISTINCT m.id) AS matches,
       SUM(ts.yellow_cards) AS total_yellows,
       ROUND(SUM(ts.yellow_cards)::numeric / NULLIF(COUNT(DISTINCT m.id), 0), 2) AS yellows_per_game
FROM referees r
JOIN matches m ON m.referee_id = r.id
JOIN match_team_stats ts ON ts.match_id = m.id
GROUP BY r.name
HAVING COUNT(DISTINCT m.id) > 10
ORDER BY yellows_per_game DESC;

-- Evolución de valor de mercado de un jugador
SELECT mv.recorded_at, mv.value_eur, t.name AS club
FROM market_values mv
JOIN players p ON p.id = mv.player_id
LEFT JOIN teams t ON t.id = mv.team_id
WHERE p.sofascore_id = 12345
ORDER BY mv.recorded_at;
```

---

## Visualizar Datos (Paso a Paso)

### Opción A: pgAdmin (UI)

1. Abrí `http://localhost:5050`.
2. Login:
   - Email: `admin@football.com`
   - Password: `admin123`
3. Agregar servidor:
   - Name: `football-db`
   - Host: `postgres`
   - Port: `5432`
   - Username: `football`
   - Password: `football123`
4. Navegar tablas:
   - `Servers > football-db > Databases > football_data > Schemas > public > Tables`
5. Ver datos rápido:
   - Clic derecho en una tabla > `View/Edit Data` > `All Rows`
6. Ejecutar SQL:
   - `Tools > Query Tool`
   - Pegar una query de la sección "Queries Útiles"
   - Ejecutar con botón Run.

### Opción B: Consola SQL (psql en Docker)

```bash
# Listar tablas
docker exec football_db psql -U football -d football_data -c "\dt"

# Conteos rápidos
docker exec football_db psql -U football -d football_data -c "select count(*) from countries;"
docker exec football_db psql -U football -d football_data -c "select count(*) from competitions;"

# Query de ejemplo
docker exec football_db psql -U football -d football_data -c "select name, code_iso2 from countries order by name limit 10;"
```

### Opción C: Script Python de lectura rápida

```python
from sqlalchemy import create_engine, text
from config.settings import settings

engine = create_engine(settings.DATABASE_URL_SYNC)
with engine.connect() as conn:
    rows = conn.execute(text("SELECT name, code_iso2 FROM countries ORDER BY name LIMIT 10"))
    for r in rows:
        print(r)
```

---

## Próximos Pasos

1. **Alembic** - migraciones versionadas
   ```bash
   alembic init migrations
   alembic revision --autogenerate -m "initial"
   alembic upgrade head
   ```

2. **Scraper de árbitros** (Promiedos) - datos de arbitraje por partido en Argentina
3. **API REST** - FastAPI con endpoints para consultar los datos
4. **Dashboard de análisis** - explorar datos para definir hipótesis de negocio

---

## Acceso a pgAdmin

- URL: `http://localhost:5050`
- Email: `admin@football.com`
- Password: `admin123`
- Servidor: `postgres` / puerto `5432`

---

## Operacion Productiva (Windows)

### Arranque completo

```powershell
.\scripts\start_prod.ps1
```

Esto levanta:
- `docker compose` (PostgreSQL, Redis, pgAdmin)
- migraciones + seed + data marts (si no usas `-SkipBootstrap`)
- `celery worker`
- `celery beat`
- `uvicorn` API interna en `http://127.0.0.1:8001`

Logs:
- `logs/celery_worker.log`
- `logs/celery_beat.log`
- `logs/api.log`

### Arranque rapido (sin bootstrap)

```powershell
.\scripts\start_prod.ps1 -SkipBootstrap
```

### Healthcheck operativo

```powershell
.\scripts\check_prod_health.ps1
```

Incluye:
- salud de API
- estado de contenedores
- estado de jobs de pipeline (ultima hora)
- resumen de calidad de datos

### Detener stack

```powershell
.\scripts\stop_prod.ps1
```

---

## Data Quality

### Job diario
- Celery Beat ejecuta `pipeline.run_data_quality_checks` diariamente.
- Reglas incluidas:
  - duplicados por `sofascore_id` en `players`
  - duplicados por `sofascore_id` en `teams`
  - `matches` con campos criticos nulos
  - `matches` finalizados sin score
  - `matches` no jugados con score informado

Resultados:
- tabla `data_quality_issues`
- endpoint `GET /quality/issues`
- endpoint `GET /quality/summary`

---

## Data Marts y API de Producto

Marts materializados (`analytics`):
- `dm_scouting_player_season`
- `dm_betting_team_form`
- `dm_content_team_trending`

Refresh diario:
- Celery Beat ejecuta `pipeline.refresh_data_marts`

Endpoints read-only:
- `GET /mart/scouting`
- `GET /mart/betting`
- `GET /mart/content`
- `GET /v1/content/trending/teams`
- `GET /v1/content/trending/players`
- `GET /v1/content/matches/hot`
- `GET /v1/content/stories/candidates`
- `GET /v1/content/stories/feed`
- `GET /players`
- `GET /teams`
- `GET /matches`
- `GET /stats`
- `GET /metrics`

KPIs (business observability):
- `GET /kpi/summary`
- `GET /kpi/executive`
- `GET /kpi/history`
- `POST /kpi/snapshot`
- `GET /kpi/coverage/by-competition`
- `GET /kpi/content/coverage`
- `POST /kpi/content/priorities/snapshot`
- `GET /kpi/content/priorities/latest`
- `GET /kpi/content/priorities/history`
- Catalog: `docs/kpi_catalog.md`
