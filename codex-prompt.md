# PROMPT PARA CODEX — Proyecto: Football Intelligence App

---

## CONTEXTO GENERAL DEL PROYECTO

Estás trabajando en una aplicación web full-stack de fútbol impulsada por IA. El proyecto nació como una app centrada en **Talleres de Córdoba** (Argentina), pero evolucionó hacia una plataforma más amplia que cubre **selecciones nacionales** (iniciando con la Selección Argentina) y que a futuro cubrirá cualquier equipo o liga.

La visión es construir la **primera red social de fútbol argentino con IA integrada**: un lugar donde los hinchas puedan seguir estadísticas en tiempo real, explorar jugadores en profundidad, y competir en trivias contra la IA o contra otros usuarios.

---

## STACK TECNOLÓGICO DEFINIDO

### Backend
- **Python 3.11+** con **FastAPI** (async)
- **SQLAlchemy** para ORM con **SQLite** en desarrollo, **PostgreSQL** en producción
- **Pydantic v2** para validación de schemas
- **Playwright + BeautifulSoup4** para scraping
- **httpx** para llamadas HTTP asíncronas
- **schedule** para cron jobs de scraping
- **Redis (Upstash)** para caché
- **Celery** (planeado para tareas async de mayor escala)

### Frontend
- **Next.js 14+** con App Router y **TypeScript**
- **TailwindCSS** para estilos base
- **shadcn/ui** para componentes
- **Lucide React** para iconografía (NO usar emojis como íconos)
- **SWR** para data fetching y revalidación
- **Socket.io** o **Supabase Realtime** para actualizaciones en vivo
- **Framer Motion** para animaciones (planeado)

### Infraestructura
- **Vercel** para el frontend (free tier)
- **Railway** para backend + PostgreSQL + scheduler (free tier)
- **Upstash Redis** para caché (free tier)
- **GitHub Actions** para CI/CD y cron jobs adicionales

### IA
- **Claude API (Anthropic)** — modelo `claude-sonnet-4-20250514`
- Usada para: estadísticas enriquecidas, trivias, resúmenes de partidos, predicciones
- La app ya tiene integración directa con la API de Anthropic en el frontend (artifact React)

---

## LO QUE YA ESTÁ CONSTRUIDO

### 1. Infraestructura Base (Día 1)
Se definió la estructura completa del proyecto:

```
football-app/
├── backend/
│   ├── scrapers/
│   │   ├── sofascore.py       # Scraper principal (API JSON no oficial de Sofascore)
│   │   └── sync_talleres.py   # Script de sincronización inicial
│   ├── database.py            # Config SQLAlchemy
│   ├── models.py              # Match, MatchEvent, MatchStats
│   ├── schemas.py             # Schemas Pydantic
│   ├── main.py                # FastAPI app con endpoints REST
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx           # Home con partido en vivo
│   │   └── partidos/page.tsx  # Listado de todos los partidos
│   ├── components/
│   │   ├── MatchCard.tsx
│   │   ├── MatchEvents.tsx
│   │   └── MatchStats.tsx
│   ├── lib/api.ts
│   └── types/index.ts
```

### 2. Modelos de Base de Datos

```python
# Match: id, home_team, away_team, home_score, away_score,
#        status (scheduled|live|finished), date, competition
# MatchEvent: id, match_id, minute, type (goal|card|substitution|other), text
# MatchStats: match_id, possession_home/away, shots_home/away, shots_on_target_home/away
```

### 3. API Endpoints Implementados

```
GET  /                          # Health check
GET  /matches                   # Todos los partidos (con filtro ?status=)
GET  /matches/latest            # Último partido
GET  /matches/live              # Partido en vivo (404 si no hay)
GET  /matches/{id}              # Partido específico
GET  /matches/{id}/events       # Eventos del partido
GET  /matches/{id}/stats        # Estadísticas del partido
POST /matches                   # Crear partido (usado por scrapers)
```

### 4. Scraper de Sofascore

El scraper usa la API JSON no documentada pero pública de Sofascore:
- `api.sofascore.com/api/v1/team/{team_id}/events/last/0`
- `api.sofascore.com/api/v1/team/{team_id}/events/next/0`
- `api.sofascore.com/api/v1/event/{event_id}/statistics`
- ID de Talleres en Sofascore: **5763**

Se implementó rate limiting, manejo de errores, y mapeo de status codes de Sofascore a nuestro modelo.

### 5. Scheduler Automático (Día 2)

Sistema de sincronización automática:
- Corre cada **15 minutos** en condiciones normales
- Detecta cambios antes de actualizar (evita writes innecesarios)
- Actualiza stats de partidos live/finished automáticamente

### 6. UI Components

- **MatchCard**: Marcador con equipos, estado (EN VIVO con animación), fecha
- **MatchEvents**: Timeline de eventos con íconos por tipo (gol, tarjeta, cambio)
- **MatchStats**: Barras de progreso para posesión, tiros, tiros al arco
- Actualización automática cada 30 segundos vía `setInterval`

### 7. Deploy Configurado

- Frontend en **Vercel** (listo)
- Backend en **Railway** con PostgreSQL
- CORS configurado para producción
- Scheduler como servicio separado en Railway

### 8. Artifact React: Player Profile (Selección Argentina)

Se construyó un componente React completo (`.jsx`) para explorar jugadores de la Selección Argentina con:

**Features implementadas:**
- Sidebar con los 16 jugadores del plantel, filtrables
- Hero card con foto de perfil (Wikipedia Commons) o avatar con número de dorsal
- Gradiente dinámico de fondo que cambia por jugador (cada uno tiene su `color` único)
- Integración directa con **Claude API** para fetchear estadísticas en tiempo real:
  - Goles y asistencias de carrera
  - Partidos y goles en la Selección
  - Títulos con Argentina
  - Valor de mercado, pie hábil, altura
  - Bio (2 frases) y dato curioso
- **Wave chart** SVG de rendimiento histórico (generado por IA)
- 6 StatPills con íconos de Lucide React
- Carrusel de compañeros clickeables
- Barra de logros colectivos (Qatar 2022, Copa América 2024, Finalissima 2022)
- Shimmer loading states
- Animación de entrada por jugador (`fadeUp`)
- Tipografía: **Bebas Neue** (display) + **Rajdhani** (body)
- **SIN emojis** — todos los íconos son de `lucide-react`

**Datos del plantel cargados:**
Messi (#10), E.Martínez (#23), J.Álvarez (#9), De Paul (#7), L.Martínez (#22),
E.Fernández (#24), Mac Allister (#20), Otamendi (#17), Romero (#13), Molina (#26),
L.Martínez (#25), Dybala (#21), Paredes (#5), Acuña (#8), Armani (#1), Di María (#11)

---

## FUENTES DE DATOS (SIN APIs DE PAGO)

### Sofascore (principal)
```
https://api.sofascore.com/api/v1/...
```
JSON público no documentado. Datos en tiempo real, stats, ratings de jugadores.

### Transfermarkt
```
https://www.transfermarkt.com.ar/...
```
Valores de mercado, historial de transferencias, lesiones.

### Promiedos
```
https://www.promiedos.com.ar/
```
Fixture, promedios de descenso, resultados Liga Profesional Argentina.

### ESPN AR
```
https://www.espn.com.ar/futbol/
```
Minuto a minuto, formaciones, noticias.

### Claude API (Anthropic)
```
https://api.anthropic.com/v1/messages
modelo: claude-sonnet-4-20250514
```
Para enriquecimiento de datos, trivias, análisis táctico, resúmenes.

**Reglas de scraping implementadas:**
- Respetar robots.txt
- Rate limiting: mínimo 10 segundos entre requests al mismo dominio
- Cache agresivo con Redis (TTL inteligente)
- User-Agent identificado como la app
- No scrapear contenido detrás de login

---

## ARQUITECTURA DE DATOS (DB SCHEMA)

```sql
-- Actual
matches (id, home_team, away_team, home_score, away_score, status, date, competition)
match_events (id, match_id, minute, type, text, timestamp)
match_stats (id, match_id, possession_h/a, shots_h/a, shots_on_target_h/a, updated_at)

-- Próximo (pendiente de implementar)
teams (id, name, short_name, country, league, sofascore_id, color, logo_url)
players (id, team_id, name, number, position, age, nationality, market_value, photo_url)
player_stats (id, player_id, season, goals, assists, matches, minutes, rating)
users (id, email, name, avatar, created_at)
trivia_questions (id, player_id, question, options jsonb, correct_answer, difficulty)
trivia_sessions (id, user_id, mode, score, questions_answered, created_at)
```

---

## PLANES A FUTURO (ROADMAP)

### FASE 1 — MVP Actual (EN PROGRESO)
- [x] Scraper Sofascore para Talleres
- [x] API REST FastAPI
- [x] UI básica partidos en vivo
- [x] Artifact React: Player Profile Selección Argentina
- [x] Deploy Vercel + Railway
- [ ] Integrar el artifact de Player Profile en Next.js
- [ ] Página `/seleccion/argentina` con el player explorer
- [ ] Notificaciones push cuando Talleres anota (OneSignal)
- [ ] PWA (manifest + service worker)

### FASE 2 — Auth + Social (Próximo)
- [ ] Login con Google (NextAuth.js)
- [ ] Perfiles de usuario
- [ ] Sistema de comentarios en partidos
- [ ] Reacciones (like/dislike/fuego) en eventos
- [ ] Chat en tiempo real durante partidos (Socket.io)
- [ ] Feed social básico

### FASE 3 — Trivia IA (Feature estrella)

**Modo vs IA:**
- El usuario elige un jugador de la Selección (o cualquier equipo)
- Claude genera 5-10 preguntas dinámicas sobre ese jugador
- Dificultad adaptativa (fácil → difícil según respuestas correctas)
- Categorías: estadísticas, historia, anécdotas, palmares
- Al finalizar: análisis de Claude del rendimiento del usuario

**Modo multijugador:**
- Sala de trivia en tiempo real (Socket.io)
- 2-6 jugadores simultáneos
- Preguntas generadas en tiempo real por Claude
- Ranking en vivo durante la partida
- Sistema de puntos y tabla de posiciones global

**Prompt base de Trivia (ya definido):**
```
Genera 5 preguntas de trivia sobre [JUGADOR] para nivel [DIFFICULTY].
Responde SOLO con JSON: [{question, options:[4], correct_index, explanation}]
```

### FASE 4 — Expansión de Equipos
- Soporte para múltiples ligas (Liga Profesional, Champions, Premier, etc.)
- Selector de equipo/selección en la UI
- Scraping de múltiples fuentes simultáneamente
- Dashboard de comparación entre jugadores
- Heat maps y estadísticas xG integradas

### FASE 5 — Monetización
- Partnership con casas de apuestas (Codere, Betsson) — mayor prioridad
- Plan premium con estadísticas avanzadas ilimitadas
- Publicidad contextual (Nike, Adidas, Quilmes)
- API B2B para periodistas y analistas

---

## DECISIONES TÉCNICAS TOMADAS

1. **SQLite en dev, PostgreSQL en prod** — migración transparente via SQLAlchemy
2. **No usar APIs de pago** — todo scraping con rate limiting responsable
3. **Claude API para enriquecimiento** — no para datos estructurados en tiempo real
4. **Lucide React para íconos** — sin emojis en código de producción
5. **Bebas Neue + Rajdhani** — identidad tipográfica del proyecto
6. **Color único por jugador** — sistema de colores dinámicos para fondos/acentos
7. **Monorepo** con `/backend` y `/frontend` en el mismo repo
8. **Artifact React independiente** puede integrarse como componente en Next.js

---

## CONVENCIONES DE CÓDIGO

```typescript
// Naming conventions
// Componentes: PascalCase → MatchCard, PlayerProfile
// Funciones: camelCase → fetchPlayerData, syncMatches
// Constantes: UPPER_SNAKE → SQUAD, PLAYER_IMAGES, POS_CONFIG
// Archivos: kebab-case → match-card.tsx, player-profile.tsx

// API responses siempre tienen:
// { data, error, status }
// o el schema Pydantic correspondiente

// Iconos: SIEMPRE de lucide-react, NUNCA emojis en JSX
import { Trophy, Target, Users } from "lucide-react";

// Colores: cada jugador tiene un color hex único en SQUAD[]
// El accent color se propaga a gradientes, bordes, stats
```

---

## INTEGRACIÓN DEL ARTIFACT EN NEXT.JS

El archivo `argentina-player-app-v2.jsx` es un componente React standalone.
Para integrarlo en el proyecto Next.js:

```bash
# 1. Copiar el archivo
cp argentina-player-app-v2.jsx frontend/components/PlayerExplorer.jsx

# 2. Crear la ruta
mkdir -p frontend/app/seleccion/argentina
touch frontend/app/seleccion/argentina/page.tsx
```

```typescript
// frontend/app/seleccion/argentina/page.tsx
import dynamic from 'next/dynamic';

const PlayerExplorer = dynamic(
  () => import('@/components/PlayerExplorer'),
  { ssr: false }  // Client-only por los fetch a Claude API
);

export default function ArgentinaPage() {
  return <PlayerExplorer />;
}
```

**Ajustes necesarios al integrar:**
- Mover la lógica de fetch a Claude API al backend (no exponer llamadas desde el cliente en producción)
- Crear endpoint: `POST /api/players/{player_id}/ai-stats`
- El backend hace el fetch a Claude y cachea en Redis (TTL: 24hs)
- El frontend consume `/api/players/{id}/ai-stats` en lugar de llamar a Claude directamente

---

## PRÓXIMA TAREA SUGERIDA

Integrar el componente `PlayerExplorer` en el proyecto Next.js y mover la lógica de Claude API al backend para no exponer la API key en el cliente. Luego implementar la página `/seleccion/argentina` con el explorador de jugadores, y comenzar la estructura de la feature de Trivia.

---

*Prompt generado el 12/02/2026 — Estado: MVP en desarrollo activo*
