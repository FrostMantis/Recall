import { useState, useMemo, useRef, useEffect } from "react";
import { Search, CornerDownLeft } from "lucide-react";

/* ============================================================
   SUMMON — feel-prototype (fake data)
   ------------------------------------------------------------
   Demonstrates the core interaction only:
     • summon a node by name / type / property / neighbour
     • land on it; its cluster blooms around it
     • click a neighbour to re-center ("the camera moves")
     • walk-back via the trail
   This is NOT wired to a backend. It's the visual + feel spec.
   ============================================================ */

// ---- palette (deep petrol ground, warm ember focus, cool teal relations) ----
const C = {
  ink:    "#0e1719",
  ink2:   "#0b1214",
  panel:  "#15201e",
  line:   "#283734",
  paper:  "#ece7dc",
  muted:  "#8a9b97",
  ember:  "#e8a14d",
  emberD: "#b97a32",
  teal:   "#62b4a6",
};

// flavour -> accent for the edge
const FLAVOUR = {
  lives_in:    { tint: C.teal,  word: "lives in" },
  uses_serves: { tint: C.ember, word: "uses / serves" },
  made_of:     { tint: "#c9a6d8", word: "made of" },
  other:       { tint: C.muted, word: "linked" },
};

// ---- fake graph -------------------------------------------------------------
const NODES = {
  chatcli:     { name: "chatcli", type: "project", props: { language: "Python", status: "active", repo: "github.com/you/chatcli" } },
  cc_host:     { name: "Backend host", type: "server", props: { ip: "10.0.0.21", ram: "4 GB", cpu: "2 vCPU", os: "Debian 12" } },
  cc_backup:   { name: "Backup", type: "backup", props: { versions: "last 5", location: "NAS /backups/chatcli" } },
  cc_db:       { name: "Database", type: "database", props: { engine: "Postgres", location: "localhost:5432", credentials: "in vault" } },
  cc_repo:     { name: "Source repo", type: "project-source", props: { platform: "GitHub", branch: "main" } },
  cc_update:   { name: "Push procedure", type: "procedure", props: { steps: "build → push → restart service" } },

  minecraft:   { name: "Minecraft", type: "game", props: { owner: "you" } },
  mc_smp:      { name: "Creative SMP", type: "server", props: { version: "1.20.1", loader: "Fabric", players: "you + friends" } },
  mc_sky:      { name: "Skyblock", type: "server", props: { version: "1.19.2", loader: "Paper" } },
  mc_world:    { name: "Survival 2023", type: "world", props: { seed: "—", lastPlayed: "2023-11" } },
  mc_modpack:  { name: "Fabric profile", type: "modpack", props: { mods: "Create, Sodium, Lithium, JEI", count: "47 mods" } },
  mc_saves:    { name: "Saves folder", type: "folder", props: { path: "D:\\Games\\.minecraft\\saves" } },

  tower:       { name: "Main Tower PC", type: "pc", props: { cpu: "Ryzen 7", ram: "32 GB", os: "Windows 11" } },
  nas:         { name: "NAS", type: "storage", props: { capacity: "8 TB", raid: "RAID 1" } },
};

// source -> target, flavour, label (phrased from source's side)
const LINKS = [
  ["chatcli", "cc_host",   "uses_serves", "runs on"],
  ["chatcli", "cc_db",     "uses_serves", "stores data in"],
  ["chatcli", "cc_repo",   "lives_in",    "source at"],
  ["chatcli", "cc_update", "uses_serves", "updated by"],
  ["chatcli", "cc_backup", "other",       "backed up to"],
  ["cc_host", "tower",     "lives_in",    "hosted on"],
  ["cc_backup", "nas",     "lives_in",    "stored on"],

  ["minecraft", "mc_smp",     "uses_serves", "server"],
  ["minecraft", "mc_sky",     "uses_serves", "server"],
  ["minecraft", "mc_world",   "lives_in",    "world"],
  ["minecraft", "mc_modpack", "made_of",     "modpack"],
  ["minecraft", "mc_saves",   "lives_in",    "saves in"],
  ["mc_smp", "tower",         "uses_serves", "runs on"],
  ["mc_smp", "mc_modpack",    "made_of",     "uses"],
];

function neighboursOf(id) {
  const out = [];
  for (const [s, t, fl, label] of LINKS) {
    if (s === id) out.push({ id: t, flavour: fl, label, dir: "out" });
    else if (t === id) out.push({ id: s, flavour: fl, label, dir: "in" });
  }
  // de-dup (a node could appear twice in odd graphs)
  const seen = new Set();
  return out.filter((n) => (seen.has(n.id) ? false : seen.add(n.id)));
}

function summonSearch(q) {
  const query = q.trim().toLowerCase();
  if (!query) return [];
  const results = [];
  for (const id of Object.keys(NODES)) {
    const n = NODES[id];
    let reason = null;
    if (n.name.toLowerCase().includes(query)) reason = { kind: "name", text: n.name };
    if (!reason)
      for (const [k, v] of Object.entries(n.props))
        if (String(v).toLowerCase().includes(query)) { reason = { kind: "prop", text: `${k}: ${v}` }; break; }
    if (!reason && n.type.toLowerCase().includes(query)) reason = { kind: "type", text: n.type };
    if (!reason)
      for (const nb of neighboursOf(id))
        if (NODES[nb.id].name.toLowerCase().includes(query)) { reason = { kind: "neighbour", text: `linked to ${NODES[nb.id].name}` }; break; }
    if (reason) results.push({ id, reason });
  }
  // name matches first
  return results.sort((a, b) => (a.reason.kind === "name" ? -1 : 0) - (b.reason.kind === "name" ? -1 : 0)).slice(0, 7);
}

// ---- radial layout ----------------------------------------------------------
const VB = { w: 880, h: 560, cx: 440, cy: 285, r: 200 };
function layout(focusId) {
  const nbs = neighboursOf(focusId);
  const N = nbs.length;
  return nbs.map((nb, i) => {
    const a = -Math.PI / 2 + (i * 2 * Math.PI) / Math.max(N, 1);
    return { ...nb, x: VB.cx + VB.r * Math.cos(a), y: VB.cy + VB.r * Math.sin(a) };
  });
}

export default function SummonPrototype() {
  const [focusId, setFocusId] = useState(null);
  const [trail, setTrail] = useState([]);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const inputRef = useRef(null);

  const results = useMemo(() => summonSearch(q), [q]);
  const placed = useMemo(() => (focusId ? layout(focusId) : []), [focusId]);

  function summon(id) {
    setFocusId(id);
    setTrail((t) => (t[t.length - 1] === id ? t : [...t, id]));
    setQ(""); setOpen(false);
  }
  function jumpTo(id, i) { setFocusId(id); setTrail((t) => t.slice(0, i + 1)); }

  const focused = focusId ? NODES[focusId] : null;

  return (
    <div style={S.root}>
      <style>{CSS}</style>

      {/* ---- summon bar ---- */}
      <header style={S.head}>
        <div style={S.brand}><span style={{ color: C.ember }}>✦</span> summon</div>
        <div style={S.searchWrap}>
          <Search size={16} color={C.muted} style={{ flexShrink: 0 }} />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => { setQ(e.target.value); setOpen(true); }}
            onFocus={() => setOpen(true)}
            onKeyDown={(e) => { if (e.key === "Enter" && results[0]) summon(results[0].id); if (e.key === "Escape") setOpen(false); }}
            placeholder="summon a thing…  try a name, a type, or a detail like “create” or “fabric”"
            style={S.input}
            aria-label="Summon search"
          />
          {q && <kbd style={S.kbd}><CornerDownLeft size={12} /></kbd>}
          {open && results.length > 0 && (
            <ul style={S.results}>
              {results.map((r) => (
                <li key={r.id}>
                  <button style={S.result} onClick={() => summon(r.id)}>
                    <span style={S.resName}>{NODES[r.id].name}</span>
                    <span style={S.resType}>{NODES[r.id].type}</span>
                    <span style={S.resReason}>
                      {r.reason.kind === "name" ? "" : r.reason.kind === "prop" ? `matched  ${r.reason.text}`
                        : r.reason.kind === "neighbour" ? r.reason.text : `type · ${r.reason.text}`}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </header>

      {/* ---- trail ---- */}
      {trail.length > 0 && (
        <nav style={S.trail} aria-label="Path">
          {trail.map((id, i) => (
            <span key={i} style={{ display: "inline-flex", alignItems: "center" }}>
              {i > 0 && <span style={S.trailSep}>→</span>}
              <button
                onClick={() => jumpTo(id, i)}
                style={{ ...S.crumb, color: i === trail.length - 1 ? C.ember : C.muted }}
              >{NODES[id].name}</button>
            </span>
          ))}
        </nav>
      )}

      {/* ---- stage ---- */}
      <main style={S.stage}>
        {!focused ? (
          <div style={S.empty}>
            <p style={S.emptyTitle}>Summon something.</p>
            <p style={S.emptySub}>Type a word above, or start here:</p>
            <div style={{ display: "flex", gap: 10, justifyContent: "center", marginTop: 14, flexWrap: "wrap" }}>
              {["chatcli", "minecraft", "tower"].map((id) => (
                <button key={id} style={S.chip} onClick={() => summon(id)}>{NODES[id].name}</button>
              ))}
            </div>
          </div>
        ) : (
          <div style={S.stageGrid}>
            <svg viewBox={`0 0 ${VB.w} ${VB.h}`} style={{ width: "100%", height: "auto", display: "block" }} role="img" aria-label={`Cluster around ${focused.name}`}>
              <defs>
                <radialGradient id="halo" cx="50%" cy="50%" r="50%">
                  <stop offset="0%" stopColor={C.ember} stopOpacity="0.22" />
                  <stop offset="100%" stopColor={C.ember} stopOpacity="0" />
                </radialGradient>
              </defs>

              {/* bloom group: scaling from center makes the orbit emanate outward */}
              <g key={focusId} className="bloom" style={{ transformOrigin: `${VB.cx}px ${VB.cy}px` }}>
                {/* edges */}
                {placed.map((p) => {
                  const tint = FLAVOUR[p.flavour].tint;
                  const lx = VB.cx + (p.x - VB.cx) * 0.56;
                  const ly = VB.cy + (p.y - VB.cy) * 0.56;
                  return (
                    <g key={"e" + p.id}>
                      <line x1={VB.cx} y1={VB.cy} x2={p.x} y2={p.y} stroke={tint} strokeOpacity="0.35" strokeWidth="1.5" />
                      <text x={lx} y={ly} textAnchor="middle" style={S.edgeLabel} fill={tint}>
                        {p.dir === "out" ? "" : "← "}{p.label}{p.dir === "out" ? " →" : ""}
                      </text>
                    </g>
                  );
                })}

                {/* center halo + node */}
                <circle cx={VB.cx} cy={VB.cy} r="118" fill="url(#halo)" />
                <g>
                  <circle cx={VB.cx} cy={VB.cy} r="58" fill={C.ink2} stroke={C.ember} strokeWidth="2" />
                  <text x={VB.cx} y={VB.cy - 4} textAnchor="middle" style={S.centerName}>{trunc(focused.name, 14)}</text>
                  <text x={VB.cx} y={VB.cy + 15} textAnchor="middle" style={S.centerType}>{focused.type}</text>
                </g>

                {/* neighbours */}
                {placed.map((p) => {
                  const n = NODES[p.id];
                  const tint = FLAVOUR[p.flavour].tint;
                  return (
                    <g key={p.id} className="nb" tabIndex={0} role="button" aria-label={`Move to ${n.name}`}
                       onClick={() => summon(p.id)}
                       onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") summon(p.id); }}
                       style={{ cursor: "pointer" }}>
                      <rect x={p.x - 76} y={p.y - 24} width="152" height="48" rx="10"
                            fill={C.panel} stroke={tint} strokeOpacity="0.55" strokeWidth="1.5" />
                      <text x={p.x} y={p.y - 3} textAnchor="middle" style={S.nbName}>{trunc(n.name, 17)}</text>
                      <text x={p.x} y={p.y + 13} textAnchor="middle" style={S.nbType}>{n.type}</text>
                    </g>
                  );
                })}
              </g>
            </svg>

            {/* ---- property sheet ---- */}
            <aside style={S.sheet}>
              <div style={S.sheetHead}>
                <div style={S.sheetName}>{focused.name}</div>
                <div style={S.sheetType}>{focused.type}</div>
              </div>
              <dl style={S.dl}>
                {Object.entries(focused.props).map(([k, v]) => (
                  <div key={k} style={S.row}>
                    <dt style={S.dt}>{k}</dt>
                    <dd style={S.dd}>{v}</dd>
                  </div>
                ))}
              </dl>
              <div style={S.sheetFoot}>{placed.length} linked {placed.length === 1 ? "thing" : "things"} · click any to move there</div>
            </aside>
          </div>
        )}
      </main>
    </div>
  );
}

function trunc(s, n) { return s.length > n ? s.slice(0, n - 1) + "…" : s; }

// ---- inline styles ----------------------------------------------------------
const mono = 'ui-monospace, "SF Mono", "JetBrains Mono", Menlo, monospace';
const sans = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';

const S = {
  root: { background: `radial-gradient(120% 90% at 50% 0%, ${C.ink} 0%, ${C.ink2} 100%)`, color: C.paper, fontFamily: sans, minHeight: 560, padding: "20px 22px 28px", borderRadius: 12 },
  head: { display: "flex", alignItems: "center", gap: 18 },
  brand: { fontFamily: mono, fontSize: 14, letterSpacing: "0.12em", color: C.paper, textTransform: "lowercase", flexShrink: 0 },
  searchWrap: { position: "relative", flex: 1, display: "flex", alignItems: "center", gap: 10, background: C.panel, border: `1px solid ${C.line}`, borderRadius: 10, padding: "10px 12px" },
  input: { flex: 1, background: "transparent", border: "none", outline: "none", color: C.paper, fontFamily: mono, fontSize: 14 },
  kbd: { display: "inline-flex", alignItems: "center", color: C.muted, border: `1px solid ${C.line}`, borderRadius: 5, padding: "2px 5px" },
  results: { position: "absolute", top: "calc(100% + 8px)", left: 0, right: 0, background: C.panel, border: `1px solid ${C.line}`, borderRadius: 10, listStyle: "none", margin: 0, padding: 6, zIndex: 20, boxShadow: "0 18px 40px rgba(0,0,0,0.45)" },
  result: { width: "100%", display: "flex", alignItems: "baseline", gap: 10, background: "transparent", border: "none", textAlign: "left", padding: "9px 10px", borderRadius: 7, cursor: "pointer", color: C.paper },
  resName: { fontFamily: mono, fontSize: 13.5 },
  resType: { fontSize: 11, color: C.teal },
  resReason: { fontSize: 11.5, color: C.muted, marginLeft: "auto", fontFamily: mono },

  trail: { marginTop: 14, display: "flex", alignItems: "center", flexWrap: "wrap", gap: 2, fontSize: 12.5 },
  trailSep: { color: C.line, margin: "0 6px" },
  crumb: { background: "transparent", border: "none", cursor: "pointer", fontFamily: mono, fontSize: 12.5, padding: 2 },

  stage: { marginTop: 10 },
  stageGrid: { display: "flex", gap: 18, alignItems: "stretch", flexWrap: "wrap" },

  empty: { textAlign: "center", padding: "90px 0 110px" },
  emptyTitle: { fontFamily: mono, fontSize: 22, color: C.paper, margin: 0, letterSpacing: "0.02em" },
  emptySub: { color: C.muted, fontSize: 13.5, marginTop: 8 },
  chip: { background: C.panel, color: C.paper, border: `1px solid ${C.line}`, borderRadius: 999, padding: "8px 16px", fontFamily: mono, fontSize: 13, cursor: "pointer" },

  edgeLabel: { fontFamily: mono, fontSize: 10.5, letterSpacing: "0.02em" },
  centerName: { fontFamily: mono, fontSize: 15, fill: C.paper, fontWeight: 600 },
  centerType: { fontFamily: mono, fontSize: 10.5, fill: C.ember, letterSpacing: "0.08em" },
  nbName: { fontFamily: mono, fontSize: 12.5, fill: C.paper },
  nbType: { fontFamily: sans, fontSize: 10, fill: C.muted, letterSpacing: "0.04em" },

  sheet: { flex: "1 1 240px", minWidth: 230, background: C.panel, border: `1px solid ${C.line}`, borderRadius: 12, padding: 18, alignSelf: "flex-start" },
  sheetHead: { borderBottom: `1px solid ${C.line}`, paddingBottom: 12, marginBottom: 12 },
  sheetName: { fontFamily: mono, fontSize: 16, color: C.paper },
  sheetType: { fontSize: 11.5, color: C.ember, letterSpacing: "0.08em", marginTop: 3, textTransform: "uppercase" },
  dl: { margin: 0 },
  row: { display: "flex", gap: 12, padding: "7px 0", borderBottom: `1px solid ${C.ink2}` },
  dt: { fontFamily: mono, fontSize: 10.5, color: C.muted, textTransform: "uppercase", letterSpacing: "0.06em", width: 92, flexShrink: 0, paddingTop: 1 },
  dd: { margin: 0, fontSize: 13, color: C.paper, wordBreak: "break-word" },
  sheetFoot: { marginTop: 14, fontSize: 11.5, color: C.muted, fontFamily: mono },
};

const CSS = `
.bloom { animation: bloom .42s cubic-bezier(.2,.7,.25,1) both; }
@keyframes bloom { from { opacity: 0; transform: scale(.7); } to { opacity: 1; transform: scale(1); } }
.nb:hover rect { stroke-opacity: 1 !important; }
.nb:focus-visible { outline: none; }
.nb:focus-visible rect { stroke: ${C.ember} !important; stroke-opacity: 1 !important; }
input::placeholder { color: ${C.muted}; opacity: .8; }
button:focus-visible, [role="button"]:focus-visible { outline: 2px solid ${C.ember}; outline-offset: 2px; border-radius: 8px; }
@media (prefers-reduced-motion: reduce) { .bloom { animation: none; } }
`;
