import { useState, useEffect, useRef } from "react";

// ─── SQUAD DATA ───────────────────────────────────────────────────────────────
const SQUAD = [
  { id: 1,  name: "Lionel Messi",        number: 10, pos: "Delantero",   club: "Inter Miami",        age: 37, initials: "LM", color: "#C8A84B" },
  { id: 2,  name: "Emiliano Martínez",   number: 23, pos: "Arquero",     club: "Aston Villa",        age: 32, initials: "EM", color: "#4B8FC8" },
  { id: 3,  name: "Julián Álvarez",      number: 9,  pos: "Delantero",   club: "Atlético Madrid",    age: 24, initials: "JA", color: "#C8584B" },
  { id: 4,  name: "Rodrigo De Paul",     number: 7,  pos: "Mediocampista", club: "Atlético Madrid",  age: 30, initials: "RD", color: "#4BC8A8" },
  { id: 5,  name: "Lautaro Martínez",    number: 22, pos: "Delantero",   club: "Inter Milán",        age: 27, initials: "LM", color: "#C86B4B" },
  { id: 6,  name: "Enzo Fernández",      number: 24, pos: "Mediocampista", club: "Chelsea",          age: 23, initials: "EF", color: "#4B6BC8" },
  { id: 7,  name: "Alexis Mac Allister", number: 20, pos: "Mediocampista", club: "Liverpool",        age: 25, initials: "AM", color: "#C84B8F" },
  { id: 8,  name: "Nicolás Otamendi",    number: 17, pos: "Defensor",    club: "Benfica",            age: 36, initials: "NO", color: "#7A4BC8" },
  { id: 9,  name: "Cristian Romero",     number: 13, pos: "Defensor",    club: "Tottenham",          age: 26, initials: "CR", color: "#4BC87A" },
  { id: 10, name: "Nahuel Molina",       number: 26, pos: "Defensor",    club: "Atlético Madrid",    age: 26, initials: "NM", color: "#C8A44B" },
  { id: 11, name: "Lisandro Martínez",   number: 25, pos: "Defensor",    club: "Manchester United",  age: 26, initials: "LM", color: "#C84B4B" },
  { id: 12, name: "Paulo Dybala",        number: 21, pos: "Delantero",   club: "Roma",               age: 30, initials: "PD", color: "#B44BC8" },
  { id: 13, name: "Leandro Paredes",     number: 5,  pos: "Mediocampista", club: "Roma",             age: 30, initials: "LP", color: "#4BC8C8" },
  { id: 14, name: "Marcos Acuña",        number: 8,  pos: "Defensor",    club: "Sevilla",            age: 32, initials: "MA", color: "#C8784B" },
  { id: 15, name: "Franco Armani",       number: 1,  pos: "Arquero",     club: "River Plate",        age: 37, initials: "FA", color: "#4B94C8" },
  { id: 16, name: "Ángel Di María",      number: 11, pos: "Delantero",   club: "Benfica",            age: 36, initials: "AD", color: "#C84B7A" },
];

// ─── PLAYER IMAGES (Wikipedia Commons) ───────────────────────────────────────
const PLAYER_IMAGES = {
  1:  "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Lionel-Messi-Argentina-2022-FIFA-World-Cup_%28cropped%29.jpg/400px-Lionel-Messi-Argentina-2022-FIFA-World-Cup_%28cropped%29.jpg",
  2:  "https://upload.wikimedia.org/wikipedia/commons/thumb/3/34/Emiliano_Mart%C3%ADnez_2022_%28cropped%29.jpg/400px-Emiliano_Mart%C3%ADnez_2022_%28cropped%29.jpg",
  3:  "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e5/Julian_Alvarez_Argentina_2022_FIFA_World_Cup_%28cropped%29.jpg/400px-Julian_Alvarez_Argentina_2022_FIFA_World_Cup_%28cropped%29.jpg",
};

// ─── POSITION COLORS ─────────────────────────────────────────────────────────
const POS_BADGE = {
  "Arquero":        { bg: "#1e3a5f", text: "#74ACDF" },
  "Defensor":       { bg: "#1a3a2a", text: "#4CAF81" },
  "Mediocampista":  { bg: "#3a2a1a", text: "#E8A84A" },
  "Delantero":      { bg: "#3a1a1a", text: "#E85A4A" },
};

// ─── WAVE CHART ──────────────────────────────────────────────────────────────
function WaveChart({ color, data }) {
  const points = data || [20,35,28,45,38,55,48,62,55,70,65,58,72,80,75,88,82,95];
  const h = 80;
  const w = 320;
  const maxVal = Math.max(...points);
  const coords = points.map((v, i) => {
    const x = (i / (points.length - 1)) * w;
    const y = h - (v / maxVal) * h;
    return `${x},${y}`;
  });
  const pathD = `M${coords.join(" L")} L${w},${h} L0,${h} Z`;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ height: 80 }}>
      <defs>
        <linearGradient id={`wg-${color}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.7" />
          <stop offset="100%" stopColor={color} stopOpacity="0.05" />
        </linearGradient>
      </defs>
      <path d={pathD} fill={`url(#wg-${color})`} />
      <polyline
        points={coords.join(" ")}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// ─── STAT PILL ────────────────────────────────────────────────────────────────
function StatPill({ icon, value, label, color }) {
  return (
    <div style={{
      background: "rgba(255,255,255,0.05)",
      border: "1px solid rgba(255,255,255,0.08)",
      borderRadius: 16,
      padding: "16px 20px",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      gap: 4,
      flex: 1,
      minWidth: 80,
    }}>
      <span style={{ fontSize: 22, lineHeight: 1 }}>{icon}</span>
      <span style={{ fontSize: 28, fontFamily: "'Bebas Neue', cursive", color, lineHeight: 1 }}>{value}</span>
      <span style={{ fontSize: 10, color: "rgba(255,255,255,0.45)", textTransform: "uppercase", letterSpacing: 1 }}>{label}</span>
    </div>
  );
}

// ─── MAIN APP ─────────────────────────────────────────────────────────────────
export default function ArgentinaApp() {
  const [selected, setSelected] = useState(SQUAD[0]);
  const [playerData, setPlayerData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [imgError, setImgError] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [animKey, setAnimKey] = useState(0);
  const abortRef = useRef(null);

  useEffect(() => {
    fetchPlayerData(selected);
    setImgError(false);
    setAnimKey(k => k + 1);
  }, [selected.id]);

  async function fetchPlayerData(player) {
    if (abortRef.current) abortRef.current = false;
    setLoading(true);
    setPlayerData(null);

    const prompt = `Eres un experto en fútbol argentino. Dame datos reales y actualizados del jugador "${player.name}" (${player.pos}, ${player.club}).
Responde SOLO con un JSON válido, sin markdown ni backticks, con esta estructura exacta:
{
  "goals_career": número,
  "assists_career": número,
  "matches_career": número,
  "goals_arg": número,
  "matches_arg": número,
  "titles_arg": número,
  "market_value": "string en millones €",
  "foot": "Derecho|Izquierdo|Ambidiestro",
  "height": "Xcm",
  "bio": "2 frases impactantes sobre el jugador",
  "fun_fact": "dato curioso corto",
  "form_data": [array de 12 números 0-100 representando forma reciente temporada a temporada]
}`;

    try {
      const res = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514",
          max_tokens: 1000,
          messages: [{ role: "user", content: prompt }]
        })
      });
      const data = await res.json();
      const text = data.content?.[0]?.text || "{}";
      const clean = text.replace(/```json|```/g, "").trim();
      const parsed = JSON.parse(clean);
      setPlayerData(parsed);
    } catch (e) {
      setPlayerData({
        goals_career: "—", assists_career: "—", matches_career: "—",
        goals_arg: "—", matches_arg: "—", titles_arg: "—",
        market_value: "—", foot: "—", height: "—",
        bio: "Jugador de la Selección Argentina.",
        fun_fact: "Información no disponible.",
        form_data: [40,50,55,60,58,65,70,72,68,75,80,85]
      });
    } finally {
      setLoading(false);
    }
  }

  const teammates = SQUAD.filter(p => p.id !== selected.id).slice(0, 6);
  const accent = selected.color;
  const posBadge = POS_BADGE[selected.pos] || POS_BADGE["Mediocampista"];
  const hasImg = PLAYER_IMAGES[selected.id] && !imgError;

  return (
    <>
      {/* Google Fonts */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Rajdhani:wght@300;400;500;600;700&display=swap');
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #080c14; font-family: 'Rajdhani', sans-serif; overflow: hidden; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: rgba(255,255,255,0.03); }
        ::-webkit-scrollbar-thumb { background: rgba(116,172,223,0.3); border-radius: 2px; }

        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes bgPulse {
          0%, 100% { opacity: 0.15; }
          50% { opacity: 0.25; }
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }

        .fade-in { animation: fadeSlideIn 0.5s ease forwards; }
        .player-row:hover { background: rgba(116,172,223,0.08) !important; }
        .player-row.active { background: rgba(116,172,223,0.12) !important; border-left: 3px solid #74ACDF !important; }
        .teammate-circle:hover { transform: scale(1.1); }
        .btn-view:hover { background: rgba(116,172,223,0.2) !important; }
      `}</style>

      <div style={{
        display: "flex",
        height: "100vh",
        width: "100vw",
        overflow: "hidden",
        background: "#080c14",
        position: "relative",
      }}>

        {/* ── DYNAMIC BACKGROUND ── */}
        <div style={{
          position: "absolute", inset: 0, zIndex: 0,
          background: `radial-gradient(ellipse at 60% 40%, ${accent}22 0%, transparent 60%),
                       radial-gradient(ellipse at 20% 80%, #74ACDF18 0%, transparent 50%)`,
          animation: "bgPulse 4s ease-in-out infinite",
          transition: "background 0.8s ease",
        }} />

        {/* Noise texture overlay */}
        <div style={{
          position: "absolute", inset: 0, zIndex: 0,
          backgroundImage: "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E\")",
          opacity: 0.4,
        }} />

        {/* ── SIDEBAR ── */}
        <div style={{
          width: sidebarOpen ? 220 : 0,
          minWidth: sidebarOpen ? 220 : 0,
          overflow: "hidden",
          transition: "all 0.3s ease",
          zIndex: 10,
          display: "flex",
          flexDirection: "column",
          background: "rgba(8,12,20,0.85)",
          backdropFilter: "blur(20px)",
          borderRight: "1px solid rgba(116,172,223,0.1)",
          height: "100vh",
        }}>
          {/* AFA Logo Header */}
          <div style={{
            padding: "20px 16px 12px",
            borderBottom: "1px solid rgba(255,255,255,0.06)",
            flexShrink: 0,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{
                width: 36, height: 36, borderRadius: "50%",
                background: "linear-gradient(135deg, #74ACDF, #FFFFFF)",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 18, flexShrink: 0,
              }}>🇦🇷</div>
              <div>
                <div style={{ fontSize: 11, color: "#74ACDF", letterSpacing: 2, textTransform: "uppercase" }}>Selección</div>
                <div style={{ fontSize: 16, fontFamily: "'Bebas Neue'", color: "#fff", letterSpacing: 1 }}>Argentina</div>
              </div>
            </div>
          </div>

          {/* Squad list */}
          <div style={{ overflowY: "auto", flex: 1, padding: "8px 0" }}>
            {SQUAD.map(player => (
              <div
                key={player.id}
                className={`player-row ${selected.id === player.id ? "active" : ""}`}
                onClick={() => setSelected(player)}
                style={{
                  display: "flex", alignItems: "center", gap: 10,
                  padding: "10px 16px",
                  cursor: "pointer",
                  borderLeft: "3px solid transparent",
                  transition: "all 0.2s",
                  position: "relative",
                }}
              >
                {/* Avatar */}
                <div style={{
                  width: 32, height: 32, borderRadius: "50%",
                  background: `linear-gradient(135deg, ${player.color}66, ${player.color}33)`,
                  border: `1.5px solid ${player.color}55`,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 10, fontWeight: 700, color: player.color,
                  flexShrink: 0, fontFamily: "'Bebas Neue'",
                }}>
                  {player.number}
                </div>
                <div style={{ minWidth: 0 }}>
                  <div style={{
                    fontSize: 13, fontWeight: 600, color: selected.id === player.id ? "#fff" : "rgba(255,255,255,0.75)",
                    whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                    transition: "color 0.2s",
                  }}>{player.name.split(" ").slice(-1)[0]}</div>
                  <div style={{ fontSize: 10, color: "rgba(255,255,255,0.35)", textTransform: "uppercase", letterSpacing: 0.5 }}>
                    {player.pos}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ── MAIN CONTENT ── */}
        <div style={{
          flex: 1, overflow: "auto", position: "relative", zIndex: 5,
          display: "flex", flexDirection: "column",
        }}>

          {/* Top bar */}
          <div style={{
            display: "flex", alignItems: "center", gap: 16,
            padding: "16px 24px",
            borderBottom: "1px solid rgba(255,255,255,0.05)",
            background: "rgba(8,12,20,0.5)",
            backdropFilter: "blur(10px)",
            flexShrink: 0,
          }}>
            <button
              onClick={() => setSidebarOpen(o => !o)}
              style={{
                background: "rgba(255,255,255,0.06)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 8, padding: "6px 10px",
                cursor: "pointer", color: "#fff", fontSize: 16,
              }}
            >
              {sidebarOpen ? "◀" : "▶"}
            </button>
            <div style={{ fontSize: 13, color: "rgba(255,255,255,0.4)", flex: 1 }}>
              <span style={{ color: "#74ACDF" }}>Selección Argentina</span>
              {" / "}
              <span style={{ color: "rgba(255,255,255,0.7)" }}>{selected.name}</span>
            </div>
            {/* Trivia badge */}
            <div style={{
              padding: "5px 14px",
              background: "rgba(116,172,223,0.12)",
              border: "1px solid rgba(116,172,223,0.25)",
              borderRadius: 20,
              fontSize: 11, color: "#74ACDF",
              letterSpacing: 1,
              cursor: "pointer",
              transition: "all 0.2s",
              fontWeight: 600,
            }}>
              🧠 PRÓXIMAMENTE: TRIVIA
            </div>
          </div>

          {/* Player Profile */}
          <div key={animKey} className="fade-in" style={{
            flex: 1, padding: "24px",
            display: "grid",
            gridTemplateColumns: "1fr 300px",
            gridTemplateRows: "auto 1fr",
            gap: 20,
          }}>

            {/* ── HERO CARD ── */}
            <div style={{
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 24,
              overflow: "hidden",
              position: "relative",
              display: "flex",
              flexDirection: "column",
            }}>
              {/* Hero background gradient */}
              <div style={{
                position: "absolute", inset: 0,
                background: `linear-gradient(135deg, ${accent}18 0%, transparent 50%, #74ACDF08 100%)`,
                pointerEvents: "none",
              }} />

              {/* Top section */}
              <div style={{
                display: "flex", gap: 28, padding: "28px 28px 20px",
                position: "relative",
              }}>
                {/* Player photo / avatar */}
                <div style={{ position: "relative", flexShrink: 0 }}>
                  <div style={{
                    width: 120, height: 120, borderRadius: "50%",
                    border: `3px solid ${accent}`,
                    overflow: "hidden",
                    boxShadow: `0 0 30px ${accent}44`,
                    background: `linear-gradient(135deg, ${accent}33, rgba(0,0,0,0.8))`,
                    display: "flex", alignItems: "center", justifyContent: "center",
                  }}>
                    {hasImg ? (
                      <img
                        src={PLAYER_IMAGES[selected.id]}
                        alt={selected.name}
                        onError={() => setImgError(true)}
                        style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "top" }}
                      />
                    ) : (
                      <span style={{
                        fontFamily: "'Bebas Neue'",
                        fontSize: 42, color: accent, lineHeight: 1,
                      }}>{selected.number}</span>
                    )}
                  </div>
                  {/* Number badge */}
                  <div style={{
                    position: "absolute", bottom: -2, right: -2,
                    width: 32, height: 32, borderRadius: "50%",
                    background: accent,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontFamily: "'Bebas Neue'", fontSize: 15, color: "#000",
                    border: "2px solid #080c14",
                  }}>
                    {selected.number}
                  </div>
                </div>

                {/* Name and info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6, flexWrap: "wrap" }}>
                    <span style={{
                      padding: "3px 12px",
                      background: posBadge.bg,
                      border: `1px solid ${posBadge.text}33`,
                      borderRadius: 20,
                      fontSize: 10, color: posBadge.text,
                      textTransform: "uppercase", letterSpacing: 1.5,
                      fontWeight: 600,
                    }}>{selected.pos}</span>
                    <span style={{ fontSize: 11, color: "rgba(255,255,255,0.35)" }}>
                      🏟 {selected.club}
                    </span>
                  </div>

                  <div style={{
                    fontFamily: "'Bebas Neue'",
                    fontSize: "clamp(32px, 4vw, 54px)",
                    color: "#fff",
                    lineHeight: 0.95,
                    letterSpacing: 1,
                    marginBottom: 8,
                  }}>
                    {selected.name.split(" ").slice(0, -1).join(" ")}
                    <br />
                    <span style={{ color: accent }}>
                      {selected.name.split(" ").slice(-1)[0]}
                    </span>
                  </div>

                  {/* Bio */}
                  {loading ? (
                    <div style={{
                      height: 14, width: "80%", borderRadius: 7,
                      background: "linear-gradient(90deg, rgba(255,255,255,0.06) 25%, rgba(255,255,255,0.12) 50%, rgba(255,255,255,0.06) 75%)",
                      backgroundSize: "200% 100%",
                      animation: "shimmer 1.5s infinite",
                    }} />
                  ) : (
                    <p style={{
                      fontSize: 13, color: "rgba(255,255,255,0.5)",
                      lineHeight: 1.5, maxWidth: 500,
                    }}>
                      {playerData?.bio}
                    </p>
                  )}
                </div>

                {/* Quick info */}
                <div style={{
                  display: "flex", flexDirection: "column", gap: 8,
                  flexShrink: 0, alignItems: "flex-end",
                }}>
                  {[
                    { label: "Edad", val: `${selected.age} años` },
                    { label: "Pie", val: loading ? "…" : playerData?.foot || "—" },
                    { label: "Altura", val: loading ? "…" : playerData?.height || "—" },
                    { label: "Valor", val: loading ? "…" : playerData?.market_value || "—" },
                  ].map(item => (
                    <div key={item.label} style={{ textAlign: "right" }}>
                      <div style={{ fontSize: 9, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: 1 }}>{item.label}</div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: "#fff" }}>{item.val}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Stats grid */}
              <div style={{ padding: "0 28px 20px" }}>
                <div style={{
                  fontSize: 10, color: "rgba(255,255,255,0.3)",
                  textTransform: "uppercase", letterSpacing: 2,
                  marginBottom: 12,
                }}>Estadísticas</div>

                {loading ? (
                  <div style={{ display: "flex", gap: 10 }}>
                    {[1,2,3,4,5,6].map(i => (
                      <div key={i} style={{
                        flex: 1, height: 80, borderRadius: 12,
                        background: "linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 75%)",
                        backgroundSize: "200% 100%",
                        animation: "shimmer 1.5s infinite",
                        animationDelay: `${i * 0.1}s`,
                      }} />
                    ))}
                  </div>
                ) : (
                  <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                    <StatPill icon="⚽" value={playerData?.goals_career ?? "—"} label="Goles Carrera" color={accent} />
                    <StatPill icon="🎯" value={playerData?.assists_career ?? "—"} label="Asistencias" color="#74ACDF" />
                    <StatPill icon="🏃" value={playerData?.matches_career ?? "—"} label="Partidos" color="#a0a0a0" />
                    <StatPill icon="🇦🇷" value={playerData?.goals_arg ?? "—"} label="Goles ANA" color={accent} />
                    <StatPill icon="🎽" value={playerData?.matches_arg ?? "—"} label="Caps" color="#74ACDF" />
                    <StatPill icon="🏆" value={playerData?.titles_arg ?? "—"} label="Títulos" color="#C8A84B" />
                  </div>
                )}
              </div>

              {/* Wave chart */}
              <div style={{ padding: "0 28px 20px" }}>
                <div style={{
                  fontSize: 10, color: "rgba(255,255,255,0.3)",
                  textTransform: "uppercase", letterSpacing: 2,
                  marginBottom: 8,
                }}>Rendimiento histórico</div>
                <WaveChart color={accent} data={playerData?.form_data} />
              </div>

              {/* Fun fact */}
              {!loading && playerData?.fun_fact && (
                <div style={{
                  margin: "0 28px 24px",
                  padding: "12px 16px",
                  background: `${accent}10`,
                  border: `1px solid ${accent}25`,
                  borderRadius: 12,
                  display: "flex", gap: 10, alignItems: "flex-start",
                }}>
                  <span style={{ fontSize: 16, flexShrink: 0 }}>💡</span>
                  <p style={{ fontSize: 12, color: "rgba(255,255,255,0.6)", lineHeight: 1.5 }}>
                    {playerData.fun_fact}
                  </p>
                </div>
              )}
            </div>

            {/* ── TEAMMATES ── */}
            <div style={{
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 24,
              padding: "24px",
              display: "flex",
              flexDirection: "column",
            }}>
              <div style={{
                fontSize: 10, color: "rgba(255,255,255,0.3)",
                textTransform: "uppercase", letterSpacing: 2,
                marginBottom: 20,
              }}>Compañeros</div>

              <div style={{ display: "flex", flexDirection: "column", gap: 12, flex: 1 }}>
                {teammates.map(tm => (
                  <div
                    key={tm.id}
                    className="teammate-circle"
                    onClick={() => setSelected(tm)}
                    style={{
                      display: "flex", alignItems: "center", gap: 12,
                      padding: "10px 12px",
                      background: "rgba(255,255,255,0.04)",
                      border: "1px solid rgba(255,255,255,0.07)",
                      borderRadius: 14,
                      cursor: "pointer",
                      transition: "all 0.2s",
                    }}
                  >
                    <div style={{
                      width: 40, height: 40, borderRadius: "50%",
                      background: `linear-gradient(135deg, ${tm.color}44, ${tm.color}22)`,
                      border: `1.5px solid ${tm.color}55`,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontFamily: "'Bebas Neue'",
                      fontSize: 14, color: tm.color,
                      flexShrink: 0,
                    }}>
                      {tm.number}
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 600, color: "#fff", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                        {tm.name.split(" ").slice(-1)[0]}
                      </div>
                      <div style={{ fontSize: 10, color: "rgba(255,255,255,0.35)", textTransform: "uppercase", letterSpacing: 0.5 }}>
                        {tm.pos}
                      </div>
                    </div>
                    <div style={{ marginLeft: "auto", fontSize: 16 }}>→</div>
                  </div>
                ))}
              </div>

              {/* View all */}
              <button
                onClick={() => {}}
                className="btn-view"
                style={{
                  marginTop: 16,
                  width: "100%",
                  padding: "12px",
                  background: "rgba(116,172,223,0.08)",
                  border: "1px solid rgba(116,172,223,0.2)",
                  borderRadius: 12,
                  color: "#74ACDF",
                  fontSize: 12, fontWeight: 600,
                  cursor: "pointer",
                  letterSpacing: 1,
                  textTransform: "uppercase",
                  transition: "all 0.2s",
                  fontFamily: "'Rajdhani', sans-serif",
                }}
              >
                Ver plantel completo
              </button>
            </div>

            {/* ── ARGENTINA CONTEXT BAR ── */}
            <div style={{
              gridColumn: "1 / -1",
              background: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(255,255,255,0.06)",
              borderRadius: 16,
              padding: "16px 24px",
              display: "flex", gap: 32, alignItems: "center",
            }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <span style={{ fontSize: 20 }}>🌟</span>
                <div>
                  <div style={{ fontSize: 9, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: 2 }}>Copa del Mundo</div>
                  <div style={{ fontSize: 16, fontFamily: "'Bebas Neue'", color: "#C8A84B" }}>Qatar 2022</div>
                </div>
              </div>
              <div style={{ width: 1, height: 32, background: "rgba(255,255,255,0.08)" }} />
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <span style={{ fontSize: 20 }}>🏆</span>
                <div>
                  <div style={{ fontSize: 9, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: 2 }}>Copa América</div>
                  <div style={{ fontSize: 16, fontFamily: "'Bebas Neue'", color: "#74ACDF" }}>USA 2024</div>
                </div>
              </div>
              <div style={{ width: 1, height: 32, background: "rgba(255,255,255,0.08)" }} />
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <span style={{ fontSize: 20 }}>👥</span>
                <div>
                  <div style={{ fontSize: 9, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: 2 }}>Jugadores</div>
                  <div style={{ fontSize: 16, fontFamily: "'Bebas Neue'", color: "#fff" }}>{SQUAD.length} en plantilla</div>
                </div>
              </div>
              <div style={{ width: 1, height: 32, background: "rgba(255,255,255,0.08)" }} />
              <div style={{ marginLeft: "auto", display: "flex", gap: 8, alignItems: "center" }}>
                <div style={{
                  width: 8, height: 8, borderRadius: "50%",
                  background: "#4CAF50",
                  boxShadow: "0 0 8px #4CAF50",
                  animation: "bgPulse 1s infinite",
                }} />
                <span style={{ fontSize: 11, color: "rgba(255,255,255,0.4)" }}>Datos vía IA en tiempo real</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
