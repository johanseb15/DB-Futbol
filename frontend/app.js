const API_BASE = "http://127.0.0.1:8001";
const API_KEY_HEADER = "X-API-Key";

const ui = {
  heroStatus: document.getElementById("heroStatus"),
  latencyBadge: document.getElementById("latencyBadge"),
  jsonTicker: document.getElementById("jsonTicker"),
  qualityCount: document.getElementById("qualityCount"),
  qualityHint: document.getElementById("qualityHint"),
  pipelineStatus: document.getElementById("pipelineStatus"),
  bettingList: document.getElementById("bettingList"),
  scoutingList: document.getElementById("scoutingList"),
  contentPreview: document.getElementById("contentPreview"),
  topActions: document.getElementById("topActions"),
  hotMatches: document.getElementById("hotMatches"),
  hotPlayers: document.getElementById("hotPlayers"),
  leagueStatus: document.getElementById("leagueStatus"),
  latencyMeta: document.getElementById("latencyMeta"),
  latencyLine: document.getElementById("latencyLine"),
  flowCard: document.getElementById("flowCard"),
  qualityCard: document.getElementById("qualityCard"),
  pipelineCard: document.getElementById("pipelineCard"),
  heroKpis: document.getElementById("heroKpis"),
  eventLog: document.getElementById("eventLog"),
  lastRefresh: document.getElementById("lastRefresh"),
  martLimit: document.getElementById("martLimit"),
  refreshMartsBtn: document.getElementById("refreshMartsBtn"),
  daysFilter: document.getElementById("daysFilter"),
  targetFilter: document.getElementById("targetFilter"),
  refreshContentBtn: document.getElementById("refreshContentBtn"),
  apiKeyInput: document.getElementById("apiKeyInput"),
  saveApiKeyBtn: document.getElementById("saveApiKeyBtn"),
};

const state = {
  apiKey: localStorage.getItem("fi_api_key") || "",
  eventLog: [],
  lastLatencySamples: [520, 500, 490, 460, 440, 420, 410],
};

ui.apiKeyInput.value = state.apiKey;

function logEvent(level, msg) {
  const ts = new Date().toISOString();
  state.eventLog.unshift(`[${ts}] [${level}] ${msg}`);
  state.eventLog = state.eventLog.slice(0, 40);
  ui.eventLog.innerHTML = state.eventLog.map((line) => `<div class="log-line">${line}</div>`).join("");
}

function markUpdated(el) {
  if (!el) return;
  el.classList.remove("updated");
  void el.offsetWidth;
  el.classList.add("updated");
}

function getHeaders() {
  const h = {};
  if (state.apiKey) h[API_KEY_HEADER] = state.apiKey;
  return h;
}

async function fetchJson(path) {
  const res = await fetch(`${API_BASE}${path}`, { headers: getHeaders() });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${path} -> HTTP ${res.status} ${text.slice(0, 120)}`);
  }
  return res.json();
}

async function fetchText(path) {
  const res = await fetch(`${API_BASE}${path}`, { headers: getHeaders() });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${path} -> HTTP ${res.status} ${text.slice(0, 120)}`);
  }
  return res.text();
}

function safeNum(v, d = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : d;
}

function parseMetric(metricsText, key) {
  const regex = new RegExp(`^${key}\\s+([0-9\\.]+)$`, "m");
  const m = metricsText.match(regex);
  return m ? Number(m[1]) : null;
}

function drawLatencySparkline(values) {
  const max = Math.max(...values, 1);
  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * 320;
      const y = 110 - (v / max) * 90;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  ui.latencyLine.setAttribute("points", points);
}

function setJsonTicker(payload) {
  const txt = JSON.stringify(payload, null, 2).split("\n").slice(0, 12).join("\n");
  ui.jsonTicker.textContent = txt;
}

function renderSimpleList(el, items, mapFn, empty = "No data") {
  if (!items || !items.length) {
    el.innerHTML = `<div class="list-item">${empty}</div>`;
    return;
  }
  el.innerHTML = items.map((i, idx) => `<div class="list-item">${mapFn(i, idx)}</div>`).join("");
}

function renderHeroKpis(kpis) {
  const rows = [
    { label: "freshness_lag_sec", value: safeNum(kpis.freshness_lag_sec, 0).toFixed(2) },
    { label: "coverage_ratio", value: safeNum(kpis.coverage_ratio, 0).toFixed(3) },
    { label: "quality_high_issues", value: String(safeNum(kpis.quality_high_issues, 0)) },
    { label: "pipeline_mttr_min", value: safeNum(kpis.pipeline_mttr_min, 0).toFixed(2) },
  ];
  ui.heroKpis.innerHTML = rows
    .map(
      (r) => `
        <article class="hero-kpi">
          <div class="value">${r.value}</div>
          <div class="label">${r.label}</div>
        </article>
      `
    )
    .join("");
}

async function loadHeroExecutive() {
  const data = await fetchJson("/kpi/executive");
  ui.heroStatus.textContent = `status: ${data.overall_status}`;
  renderHeroKpis(data.kpis || {});
  setJsonTicker(data.kpis || {});
}

async function loadQuality() {
  const data = await fetchJson("/quality/summary");
  ui.qualityCount.textContent = String(data.total ?? 0);
  const top = data.by_check && data.by_check.length ? data.by_check[0] : null;
  ui.qualityHint.textContent = top
    ? `${top.check_name}: ${top.count} intercepted`
    : "no issues in current window";
  markUpdated(ui.qualityCard);
}

async function loadPipelineFromMetrics() {
  const text = await fetchText("/metrics");
  const success = parseMetric(text, "scrape_jobs_success_total") || 0;
  const failed = parseMetric(text, "scrape_jobs_failed_total") || 0;
  const avgLatencySec = parseMetric(text, "scrape_jobs_avg_latency_seconds") || 0;

  const latencyMs = Math.round(avgLatencySec * 1000);
  ui.latencyBadge.textContent = `latency: ${latencyMs} ms`;
  ui.latencyMeta.textContent = `p95 target < 500ms | current avg ${avgLatencySec.toFixed(2)}s`;

  state.lastLatencySamples = [...state.lastLatencySamples.slice(-6), latencyMs > 0 ? latencyMs : state.lastLatencySamples.at(-1)];
  drawLatencySparkline(state.lastLatencySamples);

  ui.pipelineStatus.innerHTML = [
    `<li><span>jobs.success</span><strong>${Math.round(success)}</strong></li>`,
    `<li><span>jobs.failed</span><strong>${Math.round(failed)}</strong></li>`,
    `<li><span>avg.latency.ms</span><strong>${latencyMs}</strong></li>`,
  ].join("");

  markUpdated(ui.pipelineCard);
}

async function loadMarts() {
  const limit = Number(ui.martLimit.value || 10);
  const [betting, scouting, content] = await Promise.all([
    fetchJson(`/mart/betting?limit=${limit}`),
    fetchJson(`/mart/scouting?limit=${limit}`),
    fetchJson(`/mart/content?limit=${limit}`),
  ]);

  renderSimpleList(
    ui.bettingList,
    betting.items,
    (r) => `team=${r.team_id} | W:${r.last5_wins} D:${r.last5_draws} L:${r.last5_losses}`,
    "No betting mart rows"
  );

  renderSimpleList(
    ui.scoutingList,
    scouting.items,
    (r) => `player=${r.player_id} | rating=${safeNum(r.avg_rating).toFixed(2)} goals=${safeNum(r.goals)}`,
    "No scouting mart rows"
  );

  if (!content.items || !content.items.length) {
    ui.contentPreview.innerHTML = `<li>No content mart rows</li>`;
  } else {
    ui.contentPreview.innerHTML = content.items
      .slice(0, limit)
      .map((it) => `<li>team=${it.team_id} | score=${safeNum(it.trending_score).toFixed(1)} goals=${safeNum(it.goals_30d)}</li>`)
      .join("");
  }
}

async function loadCoverageTrust() {
  const days = Number(ui.daysFilter.value || 30);
  const target = Number(ui.targetFilter.value || 0.7);
  const coverage = await fetchJson(`/kpi/coverage/by-competition?days=${days}&target_min_ratio=${target}`);

  if (!coverage.items || !coverage.items.length) {
    ui.leagueStatus.innerHTML = `<li><span class="dot err"></span><span>No coverage data</span></li>`;
    return;
  }

  ui.leagueStatus.innerHTML = coverage.items
    .slice(0, 10)
    .map((league) => {
      const ratio = league.coverage_ratio == null ? "n/a" : `${(league.coverage_ratio * 100).toFixed(1)}%`;
      const dotClass = league.status === "ok" ? "ok" : "warn";
      return `<li><span class="dot ${dotClass}"></span><span>${league.competition_name} coverage=${ratio}</span></li>`;
    })
    .join("");

  markUpdated(ui.flowCard);
}

async function loadContentAnalytics() {
  const days = Number(ui.daysFilter.value || 30);
  const target = Number(ui.targetFilter.value || 0.7);

  try {
    const feed = await fetchJson(`/v1/content/stories/feed?days=${days}&target_min_ratio=${target}&hot_limit=8&player_limit=8`);

    renderSimpleList(
      ui.topActions,
      feed.top_actions,
      (a) => `${a.action_type || "action"} | ${a.competition_name || "unknown"} | coverage=${safeNum(a.coverage_ratio).toFixed(2)}`,
      "No priority actions"
    );

    renderSimpleList(
      ui.hotMatches,
      feed.hot_matches,
      (m) => `${m.home_team_name || "home"} vs ${m.away_team_name || "away"} | I=${safeNum(m.intensity_score).toFixed(1)} G=${safeNum(m.goals)}`,
      "No hot matches"
    );

    renderSimpleList(
      ui.hotPlayers,
      feed.hot_players,
      (p) => `${p.player_name || "player"} (${p.team_name || "team"}) | score=${safeNum(p.trending_score).toFixed(1)} rating=${safeNum(p.avg_rating_30d).toFixed(2)}`,
      "No hot players"
    );
  } catch (err) {
    renderSimpleList(ui.topActions, [], () => "", "Premium endpoint unavailable or unauthorized");
    renderSimpleList(ui.hotMatches, [], () => "", "Premium endpoint unavailable or unauthorized");
    renderSimpleList(ui.hotPlayers, [], () => "", "Premium endpoint unavailable or unauthorized");
    logEvent("WARN", `content feed fallback: ${String(err)}`);
  }
}

function setLastRefresh() {
  ui.lastRefresh.textContent = `last refresh ${new Date().toLocaleTimeString()}`;
}

async function refreshAll() {
  try {
    await Promise.all([
      loadHeroExecutive(),
      loadQuality(),
      loadPipelineFromMetrics(),
      loadMarts(),
      loadCoverageTrust(),
      loadContentAnalytics(),
    ]);
    setLastRefresh();
    logEvent("INFO", "dashboard refresh complete");
  } catch (err) {
    ui.heroStatus.textContent = "status: api_unreachable";
    setJsonTicker({ error: "No se pudo conectar a la API", detail: String(err) });
    logEvent("ERROR", String(err));
  }
}

function bindEvents() {
  ui.refreshMartsBtn.addEventListener("click", async () => {
    try {
      await loadMarts();
      logEvent("INFO", "marts refreshed");
    } catch (err) {
      logEvent("ERROR", String(err));
    }
  });

  ui.refreshContentBtn.addEventListener("click", async () => {
    try {
      await Promise.all([loadCoverageTrust(), loadContentAnalytics()]);
      logEvent("INFO", "content analytics refreshed");
    } catch (err) {
      logEvent("ERROR", String(err));
    }
  });

  ui.saveApiKeyBtn.addEventListener("click", () => {
    state.apiKey = ui.apiKeyInput.value.trim();
    if (state.apiKey) {
      localStorage.setItem("fi_api_key", state.apiKey);
      logEvent("INFO", "api key stored in browser localStorage");
    } else {
      localStorage.removeItem("fi_api_key");
      logEvent("INFO", "api key cleared");
    }
    refreshAll();
  });
}

bindEvents();
refreshAll();
setInterval(refreshAll, 30000);
