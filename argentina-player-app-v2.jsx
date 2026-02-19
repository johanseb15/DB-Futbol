import { useState, useEffect, useRef } from "react";
import {
  Target, Activity, Shirt, Shield, Trophy, Star,
  Users, ChevronRight, ChevronLeft, Zap, Award,
  TrendingUp, MapPin, Flag, Calendar, Ruler, Footprints,
  DollarSign, Lightbulb, BarChart2, Menu, X, Radio
} from "lucide-react";

// ─── SQUAD DATA ───────────────────────────────────────────────────────────────
const SQUAD = [
  { id: 1,  name: "Lionel Messi",        number: 10, pos: "Delantero",     club: "Inter Miami",       age: 37, color: "#C8A84B" },
  { id: 2,  name: "Emiliano Martínez",   number: 23, pos: "Arquero",       club: "Aston Villa",       age: 32, color: "#4B8FC8" },
  { id: 3,  name: "Julián Álvarez",      number: 9,  pos: "Delantero",     club: "Atlético Madrid",   age: 24, color: "#C8584B" },
  { id: 4,  name: "Rodrigo De Paul",     number: 7,  pos: "Mediocampista", club: "Atlético Madrid",   age: 30, color: "#4BC8A8" },
  { id: 5,  name: "Lautaro Martínez",    number: 22, pos: "Delantero",     club: "Inter Milán",       age: 27, color: "#C86B4B" },
  { id: 6,  name: "Enzo Fernández",      number: 24, pos: "Mediocampista", club: "Chelsea",           age: 23, color: "#4B6BC8" },
  { id: 7,  name: "Alexis Mac Allister", number: 20, pos: "Mediocampista", club: "Liverpool",         age: 25, color: "#C84B8F" },
  { id: 8,  name: "Nicolás Otamendi",    number: 17, pos: "Defensor",      club: "Benfica",           age: 36, color: "#7A4BC8" },
  { id: 9,  name: "Cristian Romero",     number: 13, pos: "Defensor",      club: "Tottenham",         age: 26, color: "#4BC87A" },
  { id: 10, name: "Nahuel Molina",       number: 26, pos: "Defensor",      club: "Atlético Madrid",   age: 26, color: "#C8A44B" },
  { id: 11, name: "Lisandro Martínez",   number: 25, pos: "Defensor",      club: "Manchester United", age: 26, color: "#C84B4B" },
  { id: 12, name: "Paulo Dybala",        number: 21, pos: "Delantero",     club: "Roma",              age: 30, color: "#B44BC8" },
  { id: 13, name: "Leandro Paredes",     number: 5,  pos: "Mediocampista", club: "Roma",              age: 30, color: "#4BC8C8" },
  { id: 14, name: "Marcos Acuña",        number: 8,  pos: "Defensor",      club: "Sevilla",           age: 32, color: "#C8784B" },
  { id: 15, name: "Franco Armani",       number: 1,  pos: "Arquero",       club: "River Plate",       age: 37, color: "#4B94C8" },
  { id: 16, name: "Ángel Di María",      number: 11, pos: "Delantero",     club: "Benfica",           age: 36, color: "#C84B7A" },
];

const PLAYER_IMAGES = {
  1: "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/Lionel-Messi-Argentina-2022-FIFA-World-Cup_%28cropped%29.jpg/400px-Lionel-Messi-Argentina-2022-FIFA-World-Cup_%28cropped%29.jpg",
  2: "https://upload.wikimedia.org/wikipedia/commons/thumb/3/34/Emiliano_Mart%C3%ADnez_2022_%28cropped%29.jpg/400px-Emiliano_Mart%C3%ADnez_2022_%28cropped%29.jpg",
  3: "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e5/Julian_Alvarez_Argentina_2022_FIFA_World_Cup_%28cropped%29.jpg/400px-Julian_Alvarez_Argentina_2022_FIFA_World_Cup_%28cropped%29.jpg",
};

const POS_CONFIG = {
  "Arquero":        { bg: "#1e3a5f", text: "#74ACDF", Icon: Shield },
  "Defensor":       { bg: "#1a3a2a", text: "#4CAF81", Icon: Shield },
  "Mediocampista":  { bg: "#3a2a1a", text: "#E8A84A", Icon: Activity },
  "Delantero":      { bg: "#3a1a1a", text: "#E85A4A", Icon: Target },
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
    <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", height: 80 }}>
      <defs>
        <linearGradient id={`wg-${color.replace("#","")}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.6" />
          <stop offset="100%" stopColor={color} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      <path d={pathD} fill={`url(#wg-${color.replace("#","")})`} />
      <polyline
        points={coords.join(" ")}
        fill="none" stroke={color} strokeWidth="2"
        strokeLinecap="round" strokeLinejoin="round"
      />
    </svg>
  );
}

// ─── STAT PILL ────────────────────────────────────────────────────────────────
function StatPill({ Icon, value, label, color }) {
  return (
    <div style={{
      background: "rgba(255,255,255,0.04)",
      border: "1px solid rgba(255,255,255,0.08)",
      borderRadius: 16, padding: "14px 16px",
      display: "flex", flexDirection: "column",
      alignItems: "center", gap: 4, flex: 1, minWidth: 80,
    }}>
      <Icon size={18} style={{ color }} strokeWidth={1.5} />
      <span style={{ fontSize: 26, fontFamily: "'Bebas Neue', cursive", color, lineHeight: 1 }}>{value}</span>
      <span style={{ fontSize: 9, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: 1, textAlign: "center" }}>{label}</span>
    </div>
  );
}

// ─── SHIMMER ─────────────────────────────────────────────────────────────────
function Shimmer({ w = "100%", h = 16, br = 8, delay = 0 }) {
  return (
    <div style={{
      width: w, height: h, borderRadius: br,
      background: "linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.09) 50%, rgba(255,255,255,0.04) 75%)",
      backgroundSize: "200% 100%",
      animation: `shimmer 1.5s infinite ${delay}s`,
    }} />
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

  useEffect(() => {
    fetchPlayerData(selected);
    setImgError(false);
    setAnimKey(k => k + 1);
  }, [selected.id]);

  async function fetchPlayerData(player) {
    setLoading(true);
    setPlayerData(null);

    const prompt = `Eres un experto en fútbol. Dame estadísticas reales de "${player.name}" (${player.pos}, ${player.club}).
Responde SOLO con JSON válido, sin markdown ni backticks:
{
  "goals_career": número,
  "assists_career": número,
  "matches_career": número,
  "goals_arg": número,
  "matches_arg": número,
  "titles_arg": número,
  "market_value": "string en M€",
  "foot": "Derecho|Izquierdo|Ambidiestro",
  "height": "Xcm",
  "bio": "2 frases sobre el jugador",
  "fun_fact": "un dato curioso muy corto",
  "form_data": [12 números 0-100 representando rendimiento por temporada]
}`;

    try {
      const res = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514",
          max_tokens: 1000,
          messages: [{ role: "user", content: prompt }],
        }),
      });
      const data = await res.json();
      const raw = data.content?.[0]?.text || "{}";
      const clean = raw.replace(/```json|```/g, "").trim();
      setPlayerData(JSON.parse(clean));
    } catch {
      setPlayerData({
        goals_career: "—", assists_career: "—", matches_career: "—",
        goals_arg: "—", matches_arg: "—", titles_arg: "—",
        market_value: "—", foot: "—", height: "—",
        bio: "Jugador de la Selección Argentina.",
        fun_fact: "Sin datos disponibles.",
        form_data: [40,50,55,60,58,65,70,72,68,75,80,85],
      });
    } finally {
      setLoading(false);
    }
  }

  const teammates = SQUAD.filter(p => p.id !== selected.id).slice(0, 7);
  const accent = selected.color;
  const posCfg = POS_CONFIG[selected.pos] || POS_CONFIG["Mediocampista"];
  const PosIcon = posCfg.Icon;
  const hasImg = PLAYER_IMAGES[selected.id] && !imgError;

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Rajdhani:wght@300;400;500;600;700&display=swap');
        *, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }
        body { background:#080c14; font-family:'Rajdhani',sans-serif; overflow:hidden; }
        ::-webkit-scrollbar { width:3px; }
        ::-webkit-scrollbar-thumb { background:rgba(116,172,223,0.25); border-radius:2px; }

        @keyframes fadeUp   { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:translateY(0)} }
        @keyframes bgPulse  { 0%,100%{opacity:.14} 50%{opacity:.22} }
        @keyframes shimmer  { 0%{background-position:-200% 0} 100%{background-position:200% 0} }
        @keyframes live     { 0%,100%{opacity:1} 50%{opacity:.3} }

        .fade-up   { animation: fadeUp .45s ease both; }
        .pl-row    { transition:all .18s; cursor:pointer; border-left:3px solid transparent; }
        .pl-row:hover  { background:rgba(116,172,223,.07)!important; }
        .pl-row.act    { background:rgba(116,172,223,.12)!important; border-left-color:#74ACDF!important; }
        .tm-card   { transition:transform .18s,background .18s; cursor:pointer; }
        .tm-card:hover { transform:translateY(-2px); background:rgba(255,255,255,.07)!important; }
        .btn-all   { transition:background .18s; cursor:pointer; }
        .btn-all:hover { background:rgba(116,172,223,.18)!important; }
        .toggle    { transition:background .18s; cursor:pointer; }
        .toggle:hover { background:rgba(255,255,255,.12)!important; }
      `}</style>

      <div style={{ display:"flex", height:"100vh", width:"100vw", overflow:"hidden", background:"#080c14", position:"relative" }}>

        {/* ── DYNAMIC BACKGROUND ── */}
        <div style={{
          position:"absolute", inset:0, zIndex:0, pointerEvents:"none",
          background:`radial-gradient(ellipse 60% 50% at 65% 35%, ${accent}1e 0%, transparent 70%),
                      radial-gradient(ellipse 40% 60% at 20% 75%, #74ACDF14 0%, transparent 60%)`,
          animation:"bgPulse 5s ease-in-out infinite",
          transition:"background 0.9s ease",
        }} />

        {/* ── SIDEBAR ── */}
        <div style={{
          width: sidebarOpen ? 210 : 0,
          minWidth: sidebarOpen ? 210 : 0,
          overflow:"hidden",
          transition:"all .28s ease",
          zIndex:10,
          display:"flex", flexDirection:"column",
          background:"rgba(6,10,18,.88)",
          backdropFilter:"blur(24px)",
          borderRight:"1px solid rgba(255,255,255,.06)",
        }}>
          {/* Header */}
          <div style={{ padding:"18px 14px 12px", borderBottom:"1px solid rgba(255,255,255,.05)", flexShrink:0 }}>
            <div style={{ display:"flex", alignItems:"center", gap:10 }}>
              <div style={{
                width:34, height:34, borderRadius:"50%",
                background:"linear-gradient(135deg,#74ACDF,#fff)",
                display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0,
              }}>
                <Flag size={16} color="#003087" fill="#003087" />
              </div>
              <div>
                <div style={{ fontSize:10, color:"#74ACDF", letterSpacing:2, textTransform:"uppercase" }}>Selección</div>
                <div style={{ fontSize:17, fontFamily:"'Bebas Neue'", color:"#fff", letterSpacing:1 }}>Argentina</div>
              </div>
            </div>
          </div>

          {/* List */}
          <div style={{ overflowY:"auto", flex:1, padding:"6px 0" }}>
            {SQUAD.map(pl => (
              <div
                key={pl.id}
                className={`pl-row ${selected.id === pl.id ? "act" : ""}`}
                onClick={() => setSelected(pl)}
                style={{ display:"flex", alignItems:"center", gap:10, padding:"9px 14px" }}
              >
                <div style={{
                  width:30, height:30, borderRadius:"50%",
                  background:`linear-gradient(135deg,${pl.color}55,${pl.color}22)`,
                  border:`1.5px solid ${pl.color}44`,
                  display:"flex", alignItems:"center", justifyContent:"center",
                  fontFamily:"'Bebas Neue'", fontSize:12, color:pl.color, flexShrink:0,
                }}>
                  {pl.number}
                </div>
                <div style={{ minWidth:0 }}>
                  <div style={{
                    fontSize:13, fontWeight:600,
                    color: selected.id === pl.id ? "#fff" : "rgba(255,255,255,.7)",
                    whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis",
                  }}>
                    {pl.name.split(" ").slice(-1)[0]}
                  </div>
                  <div style={{ fontSize:9, color:"rgba(255,255,255,.3)", textTransform:"uppercase", letterSpacing:.5 }}>
                    {pl.pos}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* ── MAIN ── */}
        <div style={{ flex:1, overflow:"auto", zIndex:5, display:"flex", flexDirection:"column" }}>

          {/* Topbar */}
          <div style={{
            display:"flex", alignItems:"center", gap:14, padding:"13px 20px",
            borderBottom:"1px solid rgba(255,255,255,.05)",
            background:"rgba(6,10,18,.55)", backdropFilter:"blur(12px)", flexShrink:0,
          }}>
            <button
              className="toggle"
              onClick={() => setSidebarOpen(o => !o)}
              style={{
                background:"rgba(255,255,255,.06)", border:"1px solid rgba(255,255,255,.1)",
                borderRadius:8, padding:"6px 9px", color:"#fff", display:"flex",
              }}
            >
              {sidebarOpen ? <ChevronLeft size={16}/> : <Menu size={16}/>}
            </button>
            <div style={{ fontSize:12, color:"rgba(255,255,255,.35)", flex:1 }}>
              <span style={{ color:"#74ACDF" }}>Selección Argentina</span>
              <span style={{ margin:"0 6px", opacity:.3 }}>/</span>
              <span style={{ color:"rgba(255,255,255,.7)" }}>{selected.name}</span>
            </div>
            <div style={{
              display:"flex", alignItems:"center", gap:8,
              padding:"5px 14px",
              background:"rgba(116,172,223,.09)",
              border:"1px solid rgba(116,172,223,.2)",
              borderRadius:20, fontSize:11, color:"#74ACDF",
              fontWeight:600, letterSpacing:.8,
            }}>
              <Zap size={12} />
              TRIVIA — PRÓXIMAMENTE
            </div>
          </div>

          {/* Profile grid */}
          <div
            key={animKey}
            className="fade-up"
            style={{
              flex:1, padding:"20px",
              display:"grid",
              gridTemplateColumns:"1fr 280px",
              gridTemplateRows:"1fr auto",
              gap:16,
            }}
          >
            {/* ── HERO CARD ── */}
            <div style={{
              background:"rgba(255,255,255,.025)",
              border:"1px solid rgba(255,255,255,.07)",
              borderRadius:22, overflow:"hidden", position:"relative",
              display:"flex", flexDirection:"column",
            }}>
              {/* Gradient overlay */}
              <div style={{
                position:"absolute", inset:0, pointerEvents:"none",
                background:`linear-gradient(140deg,${accent}14 0%,transparent 45%,#74ACDF07 100%)`,
              }} />

              {/* Top */}
              <div style={{ display:"flex", gap:24, padding:"24px 24px 16px", position:"relative" }}>
                {/* Photo */}
                <div style={{ position:"relative", flexShrink:0 }}>
                  <div style={{
                    width:110, height:110, borderRadius:"50%",
                    border:`3px solid ${accent}`,
                    overflow:"hidden",
                    boxShadow:`0 0 28px ${accent}40`,
                    background:`linear-gradient(135deg,${accent}30,rgba(0,0,0,.75))`,
                    display:"flex", alignItems:"center", justifyContent:"center",
                  }}>
                    {hasImg
                      ? <img src={PLAYER_IMAGES[selected.id]} alt={selected.name} onError={() => setImgError(true)}
                          style={{ width:"100%", height:"100%", objectFit:"cover", objectPosition:"top" }} />
                      : <span style={{ fontFamily:"'Bebas Neue'", fontSize:40, color:accent }}>{selected.number}</span>
                    }
                  </div>
                  <div style={{
                    position:"absolute", bottom:-2, right:-2, width:28, height:28, borderRadius:"50%",
                    background:accent, display:"flex", alignItems:"center", justifyContent:"center",
                    fontFamily:"'Bebas Neue'", fontSize:13, color:"#000",
                    border:"2px solid #080c14",
                  }}>
                    {selected.number}
                  </div>
                </div>

                {/* Name block */}
                <div style={{ flex:1, minWidth:0 }}>
                  <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:6, flexWrap:"wrap" }}>
                    <span style={{
                      display:"flex", alignItems:"center", gap:5,
                      padding:"3px 10px",
                      background:posCfg.bg, border:`1px solid ${posCfg.text}30`,
                      borderRadius:20, fontSize:10, color:posCfg.text,
                      textTransform:"uppercase", letterSpacing:1.5, fontWeight:600,
                    }}>
                      <PosIcon size={11} strokeWidth={2} />
                      {selected.pos}
                    </span>
                    <span style={{ display:"flex", alignItems:"center", gap:4, fontSize:11, color:"rgba(255,255,255,.3)" }}>
                      <MapPin size={11} />
                      {selected.club}
                    </span>
                  </div>

                  <div style={{
                    fontFamily:"'Bebas Neue'",
                    fontSize:"clamp(28px,3.5vw,50px)",
                    lineHeight:.92, letterSpacing:1, color:"#fff", marginBottom:8,
                  }}>
                    {selected.name.split(" ").slice(0,-1).join(" ")}<br/>
                    <span style={{ color:accent }}>{selected.name.split(" ").slice(-1)[0]}</span>
                  </div>

                  {loading
                    ? <Shimmer w="80%" h={13} />
                    : <p style={{ fontSize:12.5, color:"rgba(255,255,255,.45)", lineHeight:1.55, maxWidth:480 }}>{playerData?.bio}</p>
                  }
                </div>

                {/* Quick info */}
                <div style={{ display:"flex", flexDirection:"column", gap:10, flexShrink:0, alignItems:"flex-end" }}>
                  {[
                    { label:"Edad",   val: `${selected.age} años`,                          Icon: Calendar },
                    { label:"Pie",    val: loading ? "…" : (playerData?.foot  || "—"),       Icon: Footprints },
                    { label:"Altura", val: loading ? "…" : (playerData?.height || "—"),      Icon: Ruler },
                    { label:"Valor",  val: loading ? "…" : (playerData?.market_value || "—"),Icon: TrendingUp },
                  ].map(item => (
                    <div key={item.label} style={{ textAlign:"right", display:"flex", alignItems:"center", gap:6 }}>
                      <div>
                        <div style={{ fontSize:8, color:"rgba(255,255,255,.25)", textTransform:"uppercase", letterSpacing:1 }}>{item.label}</div>
                        <div style={{ fontSize:13, fontWeight:600, color:"#fff" }}>{item.val}</div>
                      </div>
                      <item.Icon size={14} style={{ color:"rgba(255,255,255,.2)" }} />
                    </div>
                  ))}
                </div>
              </div>

              {/* Stats */}
              <div style={{ padding:"0 24px 16px" }}>
                <div style={{ fontSize:9, color:"rgba(255,255,255,.25)", textTransform:"uppercase", letterSpacing:2, marginBottom:10, display:"flex", alignItems:"center", gap:6 }}>
                  <BarChart2 size={11}/> Estadísticas
                </div>
                {loading
                  ? <div style={{ display:"flex", gap:8 }}>
                      {[1,2,3,4,5,6].map(i => <Shimmer key={i} w="100%" h={76} br={14} delay={i*0.08} />)}
                    </div>
                  : <div style={{ display:"flex", gap:8, flexWrap:"wrap" }}>
                      <StatPill Icon={Target}   value={playerData?.goals_career  ?? "—"} label="Goles Carrera"  color={accent} />
                      <StatPill Icon={Activity} value={playerData?.assists_career ?? "—"} label="Asistencias"   color="#74ACDF" />
                      <StatPill Icon={Shirt}    value={playerData?.matches_career ?? "—"} label="Partidos"      color="#888" />
                      <StatPill Icon={Flag}     value={playerData?.goals_arg      ?? "—"} label="Goles ANA"     color={accent} />
                      <StatPill Icon={Users}    value={playerData?.matches_arg    ?? "—"} label="Caps"          color="#74ACDF" />
                      <StatPill Icon={Trophy}   value={playerData?.titles_arg     ?? "—"} label="Títulos"       color="#C8A84B" />
                    </div>
                }
              </div>

              {/* Wave */}
              <div style={{ padding:"0 24px 16px" }}>
                <div style={{ fontSize:9, color:"rgba(255,255,255,.25)", textTransform:"uppercase", letterSpacing:2, marginBottom:6, display:"flex", alignItems:"center", gap:6 }}>
                  <TrendingUp size={11}/> Rendimiento histórico
                </div>
                <WaveChart color={accent} data={playerData?.form_data} />
              </div>

              {/* Fun fact */}
              {!loading && playerData?.fun_fact && (
                <div style={{
                  margin:"0 24px 20px",
                  padding:"10px 14px",
                  background:`${accent}0e`,
                  border:`1px solid ${accent}22`,
                  borderRadius:12,
                  display:"flex", gap:10, alignItems:"flex-start",
                }}>
                  <Lightbulb size={15} style={{ color:accent, flexShrink:0, marginTop:1 }} />
                  <p style={{ fontSize:12, color:"rgba(255,255,255,.5)", lineHeight:1.5 }}>{playerData.fun_fact}</p>
                </div>
              )}
            </div>

            {/* ── TEAMMATES ── */}
            <div style={{
              background:"rgba(255,255,255,.025)",
              border:"1px solid rgba(255,255,255,.07)",
              borderRadius:22, padding:"20px",
              display:"flex", flexDirection:"column", gap:10,
            }}>
              <div style={{ fontSize:9, color:"rgba(255,255,255,.25)", textTransform:"uppercase", letterSpacing:2, display:"flex", alignItems:"center", gap:6 }}>
                <Users size={11}/> Compañeros
              </div>

              <div style={{ display:"flex", flexDirection:"column", gap:8, flex:1 }}>
                {teammates.map(tm => (
                  <div
                    key={tm.id}
                    className="tm-card"
                    onClick={() => setSelected(tm)}
                    style={{
                      display:"flex", alignItems:"center", gap:10,
                      padding:"9px 11px",
                      background:"rgba(255,255,255,.035)",
                      border:"1px solid rgba(255,255,255,.06)",
                      borderRadius:12,
                    }}
                  >
                    <div style={{
                      width:36, height:36, borderRadius:"50%",
                      background:`linear-gradient(135deg,${tm.color}40,${tm.color}18)`,
                      border:`1.5px solid ${tm.color}44`,
                      display:"flex", alignItems:"center", justifyContent:"center",
                      fontFamily:"'Bebas Neue'", fontSize:13, color:tm.color, flexShrink:0,
                    }}>
                      {tm.number}
                    </div>
                    <div style={{ minWidth:0, flex:1 }}>
                      <div style={{ fontSize:12.5, fontWeight:600, color:"#fff", whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis" }}>
                        {tm.name.split(" ").slice(-1)[0]}
                      </div>
                      <div style={{ fontSize:9, color:"rgba(255,255,255,.3)", textTransform:"uppercase", letterSpacing:.5 }}>{tm.pos}</div>
                    </div>
                    <ChevronRight size={14} style={{ color:"rgba(255,255,255,.2)", flexShrink:0 }} />
                  </div>
                ))}
              </div>

              <button
                className="btn-all"
                style={{
                  width:"100%", padding:"11px",
                  background:"rgba(116,172,223,.07)",
                  border:"1px solid rgba(116,172,223,.18)",
                  borderRadius:11,
                  color:"#74ACDF", fontSize:11,
                  fontWeight:600, letterSpacing:1,
                  textTransform:"uppercase",
                  fontFamily:"'Rajdhani',sans-serif",
                  display:"flex", alignItems:"center", justifyContent:"center", gap:6,
                }}
              >
                <Users size={13} /> Ver plantel completo
              </button>
            </div>

            {/* ── FOOTER BAR ── */}
            <div style={{
              gridColumn:"1 / -1",
              background:"rgba(255,255,255,.02)",
              border:"1px solid rgba(255,255,255,.05)",
              borderRadius:14, padding:"14px 20px",
              display:"flex", gap:24, alignItems:"center", flexWrap:"wrap",
            }}>
              {[
                { Icon: Star,    color:"#C8A84B", label:"Copa del Mundo",  val:"Qatar 2022"   },
                { Icon: Trophy,  color:"#74ACDF", label:"Copa América",    val:"USA 2024"      },
                { Icon: Award,   color:"#C84B8F", label:"Finalissima",     val:"Wembley 2022"  },
                { Icon: Users,   color:"#fff",    label:"Jugadores",        val:`${SQUAD.length} en plantilla` },
              ].map((item, i) => (
                <div key={i} style={{ display:"flex", alignItems:"center", gap:8 }}>
                  <item.Icon size={18} style={{ color:item.color }} />
                  <div>
                    <div style={{ fontSize:8, color:"rgba(255,255,255,.25)", textTransform:"uppercase", letterSpacing:1.5 }}>{item.label}</div>
                    <div style={{ fontSize:15, fontFamily:"'Bebas Neue'", color:item.color }}>{item.val}</div>
                  </div>
                  {i < 3 && <div style={{ width:1, height:28, background:"rgba(255,255,255,.07)", marginLeft:8 }} />}
                </div>
              ))}

              <div style={{ marginLeft:"auto", display:"flex", alignItems:"center", gap:7 }}>
                <Radio size={12} style={{ color:"#4CAF81", animation:"live 1.2s infinite" }} />
                <span style={{ fontSize:11, color:"rgba(255,255,255,.35)" }}>Datos vía IA · Claude API</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
