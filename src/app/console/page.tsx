"use client";

import { useEffect, useMemo, useState, type ReactNode, type Dispatch, type SetStateAction } from "react";
import ClimateMap from "../components/ClimateMap";

const TOP = ["Overview", "Digital Twin", "Earth Observation", "Climate", "Anomalies"] as const;
const SIDE = ["Location", "Hierarchy", "Twin State", "Details", "Risk", "Historical"] as const;
type LayerState = { satellite: boolean; terrain: boolean; anomalies: boolean; risk: boolean; events: boolean };
type ZoomRequest = { type: "in" | "out" | "reset"; nonce: number };

function Card({ title, children }: { title: string; children: ReactNode }) { return <section className="card"><header>{title}</header><div className="card-body">{children}</div></section>; }
function Metric({ label, value }: { label: string; value: string }) { return <div className="metric"><small>{label}</small><b>{value}</b></div>; }
function JsonBlock({ value }: { value: unknown }) { return <pre className="json">{value == null ? "NO DATA / SERVICE UNAVAILABLE" : JSON.stringify(value, null, 2)}</pre>; }

export default function ConsolePage() {
  const [top, setTop] = useState<(typeof TOP)[number]>("Overview");
  const [side, setSide] = useState<(typeof SIDE)[number]>("Location");
  const [selected, setSelected] = useState("INDIA");
  const [coords, setCoords] = useState("20.5937° N, 78.9629° E");
  const [layers, setLayers] = useState<LayerState>({ satellite: true, terrain: true, anomalies: false, risk: false, events: false });
  const [zoom, setZoom] = useState<ZoomRequest>();
  const [search, setSearch] = useState("");
  const [modal, setModal] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [timeline, setTimeline] = useState(75);
  const [horizon, setHorizon] = useState(7);
  const [scenario, setScenario] = useState({ temp: 2.5, precip: -15, sea: 0.4 });
  const [simulation, setSimulation] = useState(false);
  const [api, setApi] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => setTimeline(v => v >= 99 ? 0 : v + 1), 250);
    return () => clearInterval(id);
  }, [playing]);

  useEffect(() => {
    let alive = true;
    const safe = async (key: string, url: string) => {
      try { const r = await fetch(url, { cache: "no-store" }); return [key, r.ok ? await r.json() : null] as const; }
      catch { return [key, null] as const; }
    };
    setLoading(true);
    Promise.all([
      safe("health", "/api/health"), safe("rainfall", "/api/rainfall/summary/2024-07-15"),
      safe("risk", "/api/risk/summary/2024-07-15"), safe("events", "/api/extreme-events/summary/2024-07-15"),
      safe("forecast", `/api/forecast/baseline?horizon=${horizon}`), safe("twin", "/api/twin/summary"),
      safe("variables", "/api/climate/variables"), safe("models", "/api/models"),
      safe("validation", "/api/validation"), safe("provenance", "/api/provenance"),
      safe("prithvi", "/api/ai/prithvi/status"), safe("historical", "/api/historical/rainfall?limit=30"),
    ]).then(entries => { if (alive) setApi(Object.fromEntries(entries)); }).finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [horizon]);

  const doSearch = () => {
    const q = search.trim().toLowerCase();
    const known: Record<string, string> = { india: "INDIA", chennai: "Tamil Nadu", "tamil nadu": "Tamil Nadu", delhi: "Delhi", mumbai: "Maharashtra", bengaluru: "Karnataka", bangalore: "Karnataka", kolkata: "West Bengal", kerala: "Kerala" };
    if (known[q]) { setSelected(known[q]); setSide("Location"); setTop("Overview"); }
    else if (q) setModal(`NO REGISTERED LOCATION: ${search.toUpperCase()}`);
  };

  const exportState = () => {
    const blob = new Blob([JSON.stringify({ project: "India Climate Digital Twin", selected, coords, layers, scenario, horizon, timeline, api }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = "india-climate-twin-state.json"; a.click(); URL.revokeObjectURL(url);
  };

  const runSimulation = async () => {
    setSimulation(true);
    try {
      const qs = new URLSearchParams({ base_date: "2024-07-15", precipitation_delta_pct: String(scenario.precip), temperature_delta_c: String(scenario.temp), sea_level_rise_m: String(scenario.sea), scenario: "console" });
      const r = await fetch(`/api/scenarios/simulate?${qs.toString()}`, { cache: "no-store" });
      const simulationData = r.ok ? await r.json() : null;
      setApi(v => ({ ...v, simulation: simulationData }));
    } catch { setApi(v => ({ ...v, simulation: null })); }
  };

  const map = <div className="map-wrap"><ClimateMap layers={layers} onStateSelect={setSelected} onCoords={(lat, lon) => setCoords(`${lat.toFixed(4)}° N, ${lon.toFixed(4)}° E`)} zoomRequest={zoom}/><div className="map-tools"><button onClick={() => setZoom({ type: "in", nonce: Date.now() })}>+</button><button onClick={() => setZoom({ type: "out", nonce: Date.now() })}>−</button><button onClick={() => setZoom({ type: "reset", nonce: Date.now() })}>◎</button></div><span className="coords">{coords}</span><div className="layers"><b>LAYER MANAGER</b>{(["satellite", "terrain", "anomalies", "risk", "events"] as const).map(k => <button key={k} onClick={() => setLayers(v => ({ ...v, [k]: !v[k] }))}>{k.toUpperCase()} <i className={layers[k] ? "on" : ""} /></button>)}</div></div>;

  const serviceState = (key: string) => api[key] ? "CONNECTED" : "UNAVAILABLE";
  let content: ReactNode;

  if (side === "Location") content = <><div className="metrics"><Metric label="SELECTED LOCATION" value={selected}/><Metric label="API" value={serviceState("health")}/><Metric label="RAINFALL SERVICE" value={serviceState("rainfall")}/><Metric label="DATA MODE" value="LIVE API"/></div>{map}</>;
  else if (side === "Hierarchy") content = <div className="grid"><Card title="LOCATION HIERARCHY"><p>INDIA / NATIONAL DIGITAL TWIN</p>{["INDIA", "Tamil Nadu", "Delhi", "Maharashtra", "Karnataka", "Kerala", "West Bengal"].map(x => <button className="choice" key={x} onClick={() => { setSelected(x); setSide("Location"); }}>{x}</button>)}</Card><Card title="SELECTED NODE"><Metric label="NODE" value={selected}/><Metric label="COORDINATES" value={coords}/>{map}</Card></div>;
  else if (side === "Twin State") content = <div className="grid"><Card title="DIGITAL TWIN STATE"><p>Backend endpoint: <b>{serviceState("twin")}</b></p><JsonBlock value={api.twin}/></Card><Card title="PRITHVI WxC STATUS"><p>Model service: <b>{serviceState("prithvi")}</b></p><JsonBlock value={api.prithvi}/></Card></div>;
  else if (side === "Details") content = <div className="grid"><Card title="CLIMATE VARIABLES"><JsonBlock value={api.variables}/></Card><Card title="RAINFALL DATASET"><JsonBlock value={api.rainfall}/></Card></div>;
  else if (side === "Risk") content = <div className="grid"><Card title="CLIMATE RISK"><JsonBlock value={api.risk}/></Card><Card title="RISK MAP">{setLayersForRisk(setLayers)}{map}</Card></div>;
  else content = <div className="grid"><Card title="HISTORICAL RAINFALL"><JsonBlock value={api.historical}/></Card><Card title="VALIDATION"><JsonBlock value={api.validation}/></Card></div>;

  if (top === "Digital Twin") content = <div className="grid"><Card title="SCENARIO BUILDER"><label>Temperature change <b>{scenario.temp}°C</b><input type="range" min="-3" max="5" step="0.5" value={scenario.temp} onChange={e => setScenario(s => ({ ...s, temp: Number(e.target.value) }))}/></label><label>Precipitation variance <b>{scenario.precip}%</b><input type="range" min="-50" max="100" value={scenario.precip} onChange={e => setScenario(s => ({ ...s, precip: Number(e.target.value) }))}/></label><label>Sea-level rise <b>{scenario.sea}m</b><input type="range" min="0" max="1" step="0.1" value={scenario.sea} onChange={e => setScenario(s => ({ ...s, sea: Number(e.target.value) }))}/></label><button className="primary" onClick={runSimulation}>{simulation ? "SIMULATION REQUESTED" : "RUN BACKEND SIMULATION"}</button></Card><Card title="SIMULATION RESULT"><JsonBlock value={api.simulation}/></Card></div>;
  if (top === "Earth Observation") content = <div className="grid"><Card title="DATA ASSIMILATION"><p>IMD rainfall API: <b>{serviceState("rainfall")}</b></p><p>Sentinel-2 / Prithvi-EO: <b>{serviceState("prithvi")}</b></p><p>ERA5 / climate variables: <b>{serviceState("variables")}</b></p></Card><Card title="PROVENANCE"><JsonBlock value={api.provenance}/></Card></div>;
  if (top === "Climate") content = <div className="grid"><Card title="LIVE BASELINE FORECAST"><div className="horizon">{[1, 3, 7, 14].map(h => <button key={h} className={horizon === h ? "active" : ""} onClick={() => setHorizon(h)}>{h}D</button>)}</div><JsonBlock value={api.forecast}/></Card><Card title="MODEL CATALOGUE"><JsonBlock value={api.models}/></Card></div>;
  if (top === "Anomalies") content = <div className="grid"><Card title="EXTREME EVENTS"><JsonBlock value={api.events}/></Card><Card title="CLIMATE RISK"><JsonBlock value={api.risk}/></Card></div>;

  return <main className="shell"><style>{`.shell{height:100vh;background:#081014;color:#dbe7ed;font:14px Arial,sans-serif;display:flex;flex-direction:column;overflow:hidden}.top{height:64px;background:#141c21;border-bottom:1px solid #35434b;display:flex;align-items:center;gap:16px;padding:0 18px}.brand{font-weight:800;font-size:20px;color:#8ed5ff;white-space:nowrap}.top nav{display:flex;flex:1;height:100%}.top nav button,.actions button{background:none;border:0;color:#aebdc6;font:700 10px monospace;padding:0 10px;cursor:pointer}.top nav button.active{color:#55d9ff;border-bottom:2px solid #55d9ff}.actions{display:flex;align-items:center;gap:5px}.search{display:flex;border:1px solid #35434b}.search input{width:180px;background:none;border:0;color:white;padding:8px;outline:0}.search button{padding:8px}.work{flex:1;display:grid;grid-template-columns:220px 1fr;min-height:0}.side{background:#141c21;border-right:1px solid #35434b;display:flex;flex-direction:column}.side h3{padding:15px;margin:0;border-bottom:1px solid #35434b}.side button{border:0;background:none;color:#aebdc6;text-align:left;padding:11px 15px;font:700 10px monospace;cursor:pointer}.side button.active,.side button:hover{background:#00bfdc;color:#002f38}.side .bottom{margin-top:auto;border-top:1px solid #35434b}.main{min-width:0;display:flex;flex-direction:column}.head{padding:12px 18px;border-bottom:1px solid #35434b;display:flex;justify-content:space-between}.head h1{font-size:17px;margin:0 0 4px}.head small,.coords{font:10px monospace;color:#7e929c}.body{flex:1;overflow:auto;padding:10px}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:#35434b}.metric{background:#151e23;padding:12px;border-bottom:2px solid #38bdf8}.metric small{display:block;color:#8fa1aa;font:9px monospace}.metric b{display:block;color:#8ed5ff;font:700 20px monospace;margin-top:4px}.map-wrap{height:calc(100vh - 185px);min-height:420px;position:relative;background:#071018}.climate-map{position:absolute;inset:0}.map-tools{position:absolute;top:12px;left:12px;z-index:5;display:flex;flex-direction:column}.map-tools button{width:32px;height:32px;background:#111a20;border:1px solid #35434b;color:white;cursor:pointer}.coords{position:absolute;bottom:8px;left:8px;background:#111a20dd;padding:6px;z-index:5}.layers{position:absolute;top:12px;right:12px;z-index:5;width:170px;background:#10191eea;border:1px solid #35434b;padding:10px}.layers b{display:block;font:9px monospace;margin-bottom:5px}.layers button{display:flex;justify-content:space-between;width:100%;border:0;background:none;color:#b7c6cd;padding:6px;font:9px monospace;cursor:pointer}.layers i{width:22px;height:11px;background:#34434b;border-radius:8px}.layers i.on{background:#38bdf8}.grid{display:grid;grid-template-columns:2fr 1fr;gap:10px}.card{background:#111a20;border:1px solid #35434b;min-width:0}.card>header{padding:10px;border-bottom:1px solid #35434b;font:700 10px monospace}.card-body{padding:14px}.card p{color:#9db0ba;font-size:12px;line-height:1.6}.card label{display:block;margin-bottom:20px;font:11px monospace}.card label b{float:right;color:#55d9ff}.card input{display:block;width:100%;margin-top:9px}.primary{background:#38bdf8;border:0;color:#002f38;padding:9px 14px;font:700 10px monospace;cursor:pointer}.json{max-height:520px;overflow:auto;background:#091219;border:1px solid #27353d;padding:10px;color:#9ddcff;font:10px monospace;white-space:pre-wrap}.choice{display:block;width:100%;margin:4px 0;background:#10191e;border:1px solid #35434b;color:#b9c8cf;padding:8px;text-align:left;cursor:pointer;font:10px monospace}.choice:hover{background:#00bfdc;color:#002f38}.horizon{display:flex;gap:4px;margin-bottom:10px}.horizon button{background:#10191e;border:1px solid #35434b;color:#aebdc6;padding:7px 12px;cursor:pointer;font:10px monospace}.horizon button.active{background:#38bdf8;color:#002f38}.tmodal{position:fixed;inset:0;background:#000b;display:grid;place-items:center;z-index:20}.tmodal>div{background:#111a20;border:1px solid #35434b;padding:20px;width:360px}.tmodal button{float:right;background:none;border:0;color:white}.timeline{height:45px;border-top:1px solid #35434b;padding:8px 15px;display:flex;gap:10px;align-items:center}.timeline input{flex:1}.loading{color:#55d9ff;font:10px monospace}@media(max-width:900px){.top nav{display:none}.work{grid-template-columns:170px 1fr}.grid{grid-template-columns:1fr}.layers{display:none}}`}</style><header className="top"><div className="brand">INDIA CLIMATE TWIN</div><nav>{TOP.map(t => <button key={t} className={top === t ? "active" : ""} onClick={() => setTop(t)}>{t.toUpperCase()}</button>)}</nav><div className="actions"><div className="search"><input value={search} onChange={e => setSearch(e.target.value)} onKeyDown={e => e.key === "Enter" && doSearch()} placeholder="Search location"/><button onClick={doSearch}>⌕</button></div><button onClick={() => setModal("SYSTEM STATUS")}>●</button><button onClick={() => setModal("SETTINGS")}>⚙</button></div></header><div className="work"><aside className="side"><h3>WORKSPACE<br/><small>NATIONAL CLIMATE OPERATIONS</small></h3>{SIDE.map(s => <button key={s} className={side === s ? "active" : ""} onClick={() => setSide(s)}>{s.toUpperCase()}</button>)}<div className="bottom"><button onClick={exportState}>EXPORT STATE</button><button onClick={() => setModal("DATA SOURCES")}>DATA SOURCES</button></div></aside><section className="main"><header className="head"><div><h1>{top} / {side}</h1><small>{selected} · {coords} · {loading ? "SYNCING API" : "LIVE API"}</small></div><b style={{color:"#55d9ff",font:"10px monospace"}}>● SYSTEM OPERATIONAL</b></header><div className="body">{content}</div>{(top === "Overview" || top === "Digital Twin") && <footer className="timeline"><button onClick={() => setPlaying(v => !v)}>{playing ? "❚❚" : "▶"}</button><span>SIMULATION TIME</span><input type="range" min="0" max="99" value={timeline} onChange={e => setTimeline(Number(e.target.value))}/><b>{timeline}%</b></footer>}</section></div>{modal && <div className="tmodal" onClick={e => e.target === e.currentTarget && setModal(null)}><div><button onClick={() => setModal(null)}>×</button><h3>{modal}</h3><p>Frontend is connected to the deployed FastAPI service through the Next.js API proxy.</p><p>Unavailable scientific datasets are shown as unavailable instead of fabricated values.</p></div></div>}</main>;
}

function setLayersForRisk(setLayers: Dispatch<SetStateAction<LayerState>>) {
  return <button className="primary" onClick={() => setLayers(v => ({ ...v, risk: !v.risk }))}>{"TOGGLE RISK LAYER"}</button>;
}
