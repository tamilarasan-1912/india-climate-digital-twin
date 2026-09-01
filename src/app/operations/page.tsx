"use client";

import { useEffect, useState } from "react";

type TwinSummary = { state_dimension: number; observations: number; dates: string[]; fused_feature_dimension: number; status: string; scientific_note: string };
type Forecast = { date: string; rainfall_mm: number; model: string };
type Validation = { baseline_rainfall_forecast: { observations: number; mae_mm: number; rmse_mm: number; bias_mm: number } | null; risk_engine: { valid_points: number; score_range: { minimum: number; maximum: number }; risk_distribution: Record<string, number> }; status: string; limitations: string[] };

type Scenario = { screening_result: { mean_hazard_score: number | null; maximum_hazard_score: number | null; risk_distribution: Record<string, number> }; modeled_effect: string; unmodeled_parameters: string[]; warning: string };

async function api<T>(path: string): Promise<T> {
  const response = await fetch(path, { cache: "no-store" });
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
  return body as T;
}

export default function OperationsPage() {
  const [twin, setTwin] = useState<TwinSummary | null>(null);
  const [forecast, setForecast] = useState<Forecast[]>([]);
  const [validation, setValidation] = useState<Validation | null>(null);
  const [scenario, setScenario] = useState<Scenario | null>(null);
  const [rainfall, setRainfall] = useState(100);
  const [precipitation, setPrecipitation] = useState(20);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    Promise.all([
      api<TwinSummary>("/api/twin/summary"),
      api<{ forecast: Forecast[] }>("/api/forecast/baseline?horizon=7"),
      api<Validation>("/api/validation"),
    ]).then(([t, f, v]) => { setTwin(t); setForecast(f.forecast); setValidation(v); }).catch(e => setError(e.message));
  }, []);

  async function runScenario() {
    setBusy(true); setError("");
    try {
      const result = await api<Scenario>(`/api/scenarios/simulate?base_date=2024-07-15&precipitation_delta_pct=${precipitation}&temperature_delta_c=0&sea_level_rise_m=0&scenario=Operational%20Sensitivity`);
      setScenario(result);
    } catch (e) { setError(e instanceof Error ? e.message : "Scenario failed"); }
    finally { setBusy(false); }
  }

  async function explain() {
    setError("");
    try {
      const result = await api<{ risk: { hazard_score: number; risk_category: string }; drivers: { factor: string; value: number; unit: string }[] }>(`/api/explain/rainfall?rainfall_mm=${rainfall}`);
      setError(`Risk: ${result.risk.risk_category.toUpperCase()} • score ${result.risk.hazard_score}. Driver: ${result.drivers[0]?.factor}`);
    } catch (e) { setError(e instanceof Error ? e.message : "Explanation failed"); }
  }

  return <main style={{minHeight:"100vh",background:"#07111b",color:"#dbeafe",fontFamily:"ui-monospace, SFMono-Regular, Menlo, monospace",padding:24}}>
    <header style={{display:"flex",justifyContent:"space-between",alignItems:"center",borderBottom:"1px solid #263748",paddingBottom:18}}>
      <div><div style={{fontSize:26,fontWeight:800,color:"#67d5ff"}}>INDIA CLIMATE DIGITAL TWIN</div><div style={{fontSize:11,opacity:.65,marginTop:5}}>OPERATIONAL SCIENTIFIC CONTROL ROOM</div></div>
      <a href="/" style={{color:"#67d5ff",textDecoration:"none",border:"1px solid #2b6075",padding:"8px 14px"}}>← MAIN TWIN</a>
    </header>

    {error && <div style={{marginTop:16,padding:12,border:"1px solid #8b3a3a",background:"#241316",color:"#fecaca",fontSize:12}}>{error}</div>}

    <section style={{display:"grid",gridTemplateColumns:"repeat(4,minmax(0,1fr))",gap:12,marginTop:18}}>
      {[["TWIN STATE", twin ? `${twin.state_dimension}-D` : "—"],["OBSERVATIONS", twin?.observations ?? "—"],["FUSED FEATURES", twin?.fused_feature_dimension ?? "—"],["VALID GRID", validation?.risk_engine.valid_points?.toLocaleString() ?? "—"]].map(([a,b])=><div key={a} style={{background:"#0d1a26",border:"1px solid #243746",padding:16}}><div style={{fontSize:10,opacity:.6}}>{a}</div><div style={{fontSize:25,color:"#4ccfff",marginTop:7,fontWeight:800}}>{b}</div></div>)}
    </section>

    <section style={{display:"grid",gridTemplateColumns:"1.25fr .75fr",gap:14,marginTop:14}}>
      <div style={{background:"#0d1a26",border:"1px solid #243746",padding:18}}><h2 style={{fontSize:14,margin:0}}>BASELINE FORECAST • 7 DAYS</h2><p style={{fontSize:11,opacity:.6}}>Transparent statistical baseline; not an AI forecast.</p><div style={{display:"grid",gap:7}}>{forecast.map(x=><div key={x.date} style={{display:"flex",justifyContent:"space-between",padding:"9px 10px",background:"#101f2d",fontSize:11}}><span>{x.date}</span><strong>{x.rainfall_mm.toFixed(2)} mm</strong></div>)}</div></div>
      <div style={{background:"#0d1a26",border:"1px solid #243746",padding:18}}><h2 style={{fontSize:14,margin:0}}>VALIDATION</h2>{validation?.baseline_rainfall_forecast && <div style={{fontSize:12,lineHeight:2,marginTop:10}}>Observations: {validation.baseline_rainfall_forecast.observations}<br/>MAE: {validation.baseline_rainfall_forecast.mae_mm.toFixed(3)} mm<br/>RMSE: {validation.baseline_rainfall_forecast.rmse_mm.toFixed(3)} mm<br/>Bias: {validation.baseline_rainfall_forecast.bias_mm.toFixed(3)} mm</div>}<div style={{marginTop:10,fontSize:10,opacity:.6}}>{validation?.status}</div></div>
    </section>

    <section style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14,marginTop:14}}>
      <div style={{background:"#0d1a26",border:"1px solid #243746",padding:18}}><h2 style={{fontSize:14,margin:0}}>WHAT-IF SCENARIO</h2><label style={{display:"block",fontSize:11,marginTop:14}}>PRECIPITATION CHANGE: <strong>{precipitation}%</strong></label><input type="range" min={-100} max={300} value={precipitation} onChange={e=>setPrecipitation(Number(e.target.value))} style={{width:"100%",marginTop:10}}/><button onClick={runScenario} disabled={busy} style={{marginTop:14,padding:"10px 16px",background:"#28bce8",border:0,fontWeight:800,cursor:"pointer"}}>{busy?"RUNNING…":"RUN SCREENING SCENARIO"}</button>{scenario&&<div style={{marginTop:14,fontSize:11,lineHeight:1.8}}>Mean hazard: {scenario.screening_result.mean_hazard_score?.toFixed(2)}<br/>Maximum hazard: {scenario.screening_result.maximum_hazard_score?.toFixed(2)}<br/>Modeled: {scenario.modeled_effect}<br/><span style={{opacity:.6}}>{scenario.warning}</span></div>}</div>
      <div style={{background:"#0d1a26",border:"1px solid #243746",padding:18}}><h2 style={{fontSize:14,margin:0}}>EXPLAINABLE RISK</h2><label style={{display:"block",fontSize:11,marginTop:14}}>RAINFALL: <strong>{rainfall} mm</strong></label><input type="range" min={0} max={500} value={rainfall} onChange={e=>setRainfall(Number(e.target.value))} style={{width:"100%",marginTop:10}}/><button onClick={explain} style={{marginTop:14,padding:"10px 16px",background:"transparent",color:"#67d5ff",border:"1px solid #2b6075",fontWeight:800,cursor:"pointer"}}>EXPLAIN RISK</button><div style={{fontSize:10,opacity:.6,marginTop:14}}>Current explanation is intentionally limited to the implemented rainfall-only hazard model.</div></div>
    </section>

    <section style={{marginTop:14,background:"#0d1a26",border:"1px solid #243746",padding:18}}><h2 style={{fontSize:14,margin:0}}>SYSTEM / MODEL STATUS</h2><div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:10,marginTop:12}}>{["IMD rainfall — ACTIVE","Prithvi-EO V2 tiny — FEATURES AVAILABLE","Prithvi-WxC — INPUT BLOCKED"].map(x=><div key={x} style={{padding:12,background:"#101f2d",fontSize:11}}>{x}</div>)}</div><div style={{marginTop:12,fontSize:10,opacity:.6}}>Twin state dates: {twin?.dates?.join(" • ") || "loading"}</div></section>
  </main>;
}
