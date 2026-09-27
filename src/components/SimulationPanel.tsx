"use client";

import { useCallback, useEffect, useState } from "react";
import { endpoints, getJSON, type SimulationJobPayload, type FloodRiskAssetDamagePayload, type FloodRiskAssetRecordPayload, type ValidationMetricsPayload, type ParameterUncertaintyPayload, type CrossValidationPayload, type ValidationMetricsCatalogPayload } from "@/lib/api";
import { DataStatus, NoData, ProvenanceBadge } from "@/app/components/DataStatus";

function Metric({ label, value, unit = "", digits }: { label: string; value: unknown; unit?: string; digits?: number }) {
  const numeric = typeof value === "number" && Number.isFinite(value);
  const text = numeric
    ? (digits !== undefined ? value.toFixed(digits) : String(value))
    : value === null || value === undefined || value === "" ? null : String(value);
  return (
    <div className="metric">
      <span>{label}</span>
      {text === null
        ? <strong className="metric-none">NO DATA</strong>
        : <><strong>{text}</strong>{unit && <em>{unit}</em>}</>}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string | number | null }) {
  const text = value === null || value === undefined || value === "" ? null : String(value);
  return (
    <div className="row">
      <span>{label}</span>
      {text === null ? <b className="row-none">NO DATA</b> : <b>{text}</b>}
    </div>
  );
}

function Slider({ label, value, min, max, step, unit, onChange }: {
  label: string; value: number; min: number; max: number; step: number; unit: string; onChange: (v: number) => void;
}) {
  return (
    <label className="slider">
      <span>{label}<b>{value > 0 ? "+" : ""}{value}{unit}</b></span>
      <input type="range" min={min} max={max} step={step} value={value} onChange={e => onChange(Number(e.target.value))}/>
    </label>
  );
}

export function SimulationPanel() {
  const [jobs, setJobs] = useState<SimulationJobPayload[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedJob, setSelectedJob] = useState<SimulationJobPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  const [simType, setSimType] = useState<"scenario_sensitivity" | "gr4j_hydro" | "flood_hecras" | "hydro_hydraulic_coupled">("scenario_sensitivity");
  const [basinId, setBasinId] = useState("mahanadi_delta_sub_1");
  const [startDate, setStartDate] = useState("2024-07-01");
  const [endDate, setEndDate] = useState("2024-07-10");
  const [scenarioId, setScenarioId] = useState("");
  
  const [submitting, setSubmitting] = useState(false);

  const loadJobs = useCallback(async () => {
    const res = await getJSON<{ jobs: SimulationJobPayload[] }>(endpoints.simulationJobs());
    if (res.data) setJobs(res.data.jobs);
  }, []);

  useEffect(() => { loadJobs(); }, [loadJobs]);

  const submitJob = async () => {
    setSubmitting(true);
    setError(null);
    
    const params: Record<string, any> = {};
    if (simType === "gr4j_hydro" || simType === "hydro_hydraulic_coupled") {
      params.start_date = startDate;
      params.end_date = endDate;
    }
    if (simType === "flood_hecras" || simType === "hydro_hydraulic_coupled") {
      params.scenario_id = scenarioId || `${simType}_${Date.now()}`;
      params.terrain_asset_uri = "backend/data/basins/mahanadi_delta/dem_copernicus_30m.nc";
      params.river_centerline_path = "backend/data/basins/mahanadi_delta/hydrorivers_mahanadi.shp";
      params.landcover_asset_uri = "backend/data/basins/mahanadi_delta/worldcover_10m.nc";
    }
    if (simType === "scenario_sensitivity") {
      params.base_date = endDate;
      params.precipitation_delta_pct = 20;
      params.temperature_delta_c = 2;
      params.sea_level_rise_m = 0.5;
      params.scenario = "console_scenario";
    }

    const res = await fetch(endpoints.simulationJobs(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        simulation_type: simType,
        parameters: params,
        spatial_type: "basin",
        spatial_id: basinId,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to submit job" }));
      setError(err.detail);
    } else {
      const job = await res.json();
      setJobs(prev => [job, ...prev]);
      setSelectedJob(job);
    }
    setSubmitting(false);
  };

  const cancelJob = async (jobId: string) => {
    await fetch(endpoints.cancelSimulationJob(jobId), { method: "POST" });
    loadJobs();
  };

  const pollJob = useCallback(async (jobId: string) => {
    const res = await getJSON<SimulationJobPayload>(endpoints.simulationJob(jobId));
    if (res.data) {
      setSelectedJob(res.data);
      setJobs(prev => prev.map(j => j.job_id === jobId ? res.data! : j));
      if (res.data.status === "running" || res.data.status === "pending") {
        setTimeout(() => pollJob(jobId), 2000);
      }
    }
  }, []);

  useEffect(() => {
    if (selectedJob && (selectedJob.status === "running" || selectedJob.status === "pending")) {
      pollJob(selectedJob.job_id);
    }
  }, [selectedJob, pollJob]);

  return (
    <section className="panel" aria-label="Simulation jobs">
      <header className="panel-head">
        <h2>SIMULATION JOBS</h2>
        <span className="panel-sub">ASYNCHRONOUS EXECUTION</span>
      </header>

      <div className="sp-metrics">
        <Metric label="TOTAL JOBS" value={jobs.length}/>
        <Metric label="RUNNING" value={jobs.filter(j => j.status === "running").length}/>
        <Metric label="COMPLETED" value={jobs.filter(j => j.status === "completed").length}/>
        <Metric label="FAILED" value={jobs.filter(j => j.status === "failed").length}/>
      </div>

      <div className="slider">
        <label>SIMULATION TYPE
          <b>{simType.replace(/_/g, " ").toUpperCase()}</b>
        </label>
        <select value={simType} onChange={e => setSimType(e.target.value as typeof simType)}>
          <option value="scenario_sensitivity">Rainfall Hazard Sensitivity</option>
          <option value="gr4j_hydro">GR4J Rainfall-Runoff</option>
          <option value="flood_hecras">HEC-RAS Flood Manifest</option>
          <option value="hydro_hydraulic_coupled">GR4J → HEC-RAS Coupled</option>
        </select>
      </div>

      {(simType === "gr4j_hydro" || simType === "hydro_hydraulic_coupled") && (
        <div className="slider">
          <label>START DATE<b>{startDate}</b></label>
          <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)}/>
        </div>
      )}

      {(simType === "gr4j_hydro" || simType === "hydro_hydraulic_coupled") && (
        <div className="slider">
          <label>END DATE<b>{endDate}</b></label>
          <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)}/>
        </div>
      )}

      {(simType === "flood_hecras" || simType === "hydro_hydraulic_coupled") && (
        <div className="slider">
          <label>SCENARIO ID<b>{scenarioId || "auto"}</b></label>
          <input type="text" value={scenarioId} onChange={e => setScenarioId(e.target.value)} placeholder="Auto-generated if empty"/>
        </div>
      )}

      <button className="btn-primary" disabled={submitting} onClick={submitJob}>
        {submitting ? "SUBMITTING…" : "SUBMIT JOB"}
      </button>
      {error && <p className="scenario-warn">{error}</p>}

      <div className="table">
        <div className="table-head">
          <span>JOB ID</span><span>TYPE</span><span>STATUS</span><span>PROGRESS</span><span>STEP</span><span>CREATED</span><span>ACTIONS</span>
        </div>
        {jobs.slice(0, 20).map(job => (
          <div className="table-row" key={job.job_id} onClick={() => setSelectedJob(job)}>
            <span>{job.job_id.slice(0, 8)}…</span>
            <span>{job.simulation_type}</span>
            <span className={`status-${job.status}`}>{job.status.toUpperCase()}</span>
            <span>{job.progress ?? 0}%</span>
            <span>{job.current_step}</span>
            <span>{job.created_at.slice(0, 19).replace("T", " ")}</span>
            <span>
              {job.status === "running" || job.status === "pending" ? (
                <button className="btn-ghost" onClick={e => { e.stopPropagation(); cancelJob(job.job_id); }}>CANCEL</button>
              ) : job.status === "completed" ? (
                <button className="btn-ghost" onClick={e => { e.stopPropagation(); setSelectedJob(job); }}>VIEW</button>
              ) : null}
            </span>
          </div>
        ))}
      </div>

      {selectedJob && (
        <section className="panel" style={{ marginTop: "1rem" }}>
          <header className="panel-head"><h2>JOB DETAILS</h2></header>
          <div className="sp-metrics">
            <Metric label="JOB ID" value={selectedJob.job_id}/>
            <Metric label="TYPE" value={selectedJob.simulation_type}/>
            <Metric label="STATUS" value={selectedJob.status.toUpperCase()}/>
            <Metric label="PROGRESS" value={selectedJob.progress ?? 0} unit="%"/>
          </div>
          <div className="sp-rows">
            <Row label="CURRENT STEP" value={selectedJob.current_step ?? "—"}/>
            <Row label="BASIN" value={selectedJob.spatial_scope?.id ?? "—"}/>
            <Row label="STARTED" value={selectedJob.started_at?.slice(0, 19).replace("T", " ") ?? "—"}/>
            <Row label="COMPLETED" value={selectedJob.completed_at?.slice(0, 19).replace("T", " ") ?? "—"}/>
          </div>
          {selectedJob.error && <p className="scenario-warn">ERROR: {selectedJob.error}</p>}
          {selectedJob.result && (
            <ProvenanceBadge compact provenance={{ 
              provider: "Simulation Job", 
              dataset: selectedJob.job_id, 
              processing: selectedJob.simulation_type,
              model: `Result keys: ${Object.keys(selectedJob.result).join(", ")}`
            }} />
          )}
        </section>
      )}
    </section>
  );
}

export function FloodRiskPanel() {
  const [curves, setCurves] = useState<any>(null);
  const [assetDamage, setAssetDamage] = useState<FloodRiskAssetDamagePayload | null>(null);
  const [loading, setLoading] = useState(false);

  const [assetType, setAssetType] = useState("residential");
  const [replacementValue, setReplacementValue] = useState(5000000);
  const [floodDepth, setFloodDepth] = useState(1.5);
  const [velocity, setVelocity] = useState(1.2);
  const [duration, setDuration] = useState(48);

  useEffect(() => {
    getJSON<any>(endpoints.floodDepthDamageCurves()).then(r => r.data && setCurves(r.data));
  }, []);

  const calculateDamage = async () => {
    setLoading(true);
    const res = await fetch(endpoints.floodAssetDamage(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        asset_id: "console_test_001",
        asset_type: assetType,
        replacement_value_inr: replacementValue,
        flood_depth_m: floodDepth,
        velocity_mps: velocity,
        duration_hours: duration,
        content_value_ratio: 0.5,
      }),
    });
    if (res.ok) {
      const data = await res.json();
      setAssetDamage(data);
    }
    setLoading(false);
  };

  return (
    <section className="panel" aria-label="Flood risk">
      <header className="panel-head">
        <h2>FLOOD RISK CALCULATOR</h2>
        <span className="panel-sub">DEPTH-DAMAGE CURVES & ASSET-LEVEL</span>
      </header>

      {curves && (
        <p className="panel-note">Available curves: {Object.keys(curves.curves).join(", ")}</p>
      )}

      <div className="slider">
        <label>ASSET TYPE<b>{assetType.toUpperCase()}</b></label>
        <select value={assetType} onChange={e => setAssetType(e.target.value)}>
          <option value="residential">Residential</option>
          <option value="commercial">Commercial</option>
          <option value="industrial">Industrial</option>
          <option value="agricultural">Agricultural</option>
          <option value="infrastructure">Infrastructure</option>
        </select>
      </div>

      <div className="slider">
        <label>REPLACEMENT VALUE<b>₹{replacementValue.toLocaleString()}</b></label>
        <input type="number" value={replacementValue} onChange={e => setReplacementValue(Number(e.target.value))} min={0} step={100000}/>
      </div>

      <Slider label="FLOOD DEPTH" value={floodDepth} min={0} max={5} step={0.1} unit="m" onChange={setFloodDepth}/>
      <Slider label="VELOCITY" value={velocity} min={0} max={3} step={0.1} unit="m/s" onChange={setVelocity}/>
      <Slider label="DURATION" value={duration} min={0} max={168} step={1} unit="h" onChange={setDuration}/>

      <button className="btn-primary" disabled={loading} onClick={calculateDamage}>
        {loading ? "CALCULATING…" : "CALCULATE DAMAGE"}
      </button>

      {assetDamage && (
        <div className="sp-metrics">
          <Metric label="STRUCTURAL DAMAGE" value={assetDamage.structural_damage_inr} unit="INR"/>
          <Metric label="CONTENT DAMAGE" value={assetDamage.content_damage_inr} unit="INR"/>
          <Metric label="TOTAL DAMAGE" value={assetDamage.total_damage_inr} unit="INR"/>
          <Metric label="DAMAGE RATIO" value={assetDamage.damage_ratio} digits={4} unit=""/>
        </div>
      )}
    </section>
  );
}

export function ValidationPanel() {
  const [catalog, setCatalog] = useState<ValidationMetricsCatalogPayload | null>(null);
  const [metrics, setMetrics] = useState<ValidationMetricsPayload | null>(null);
  const [uncertainty, setUncertainty] = useState<ParameterUncertaintyPayload | null>(null);
  const [loading, setLoading] = useState(false);

  const [observed, setObserved] = useState("10,15,20,25,30,20,15,10,5,3");
  const [simulated, setSimulated] = useState("11,14,22,24,28,19,16,9,6,2");
  const [paramRanges, setParamRanges] = useState('{"X1":[100,600],"X2":[0.1,3],"X3":[20,100],"X4":[1,4]}');
  const [nSamples, setNSamples] = useState(50);

  useEffect(() => {
    getJSON<ValidationMetricsCatalogPayload>(endpoints.validationMetricsCatalog()).then(r => r.data && setCatalog(r.data));
  }, []);

  const computeMetrics = async () => {
    setLoading(true);
    const obs = observed.split(",").map(s => Number(s.trim()));
    const sim = simulated.split(",").map(s => Number(s.trim()));
    const res = await fetch(endpoints.validationHydrological(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ observed: obs, simulated: sim }),
    });
    if (res.ok) {
      const data = await res.json();
      setMetrics(data);
    }
    setLoading(false);
  };

  const runUncertainty = async () => {
    setLoading(true);
    try {
      const ranges = JSON.parse(paramRanges);
      const res = await fetch(endpoints.validationParameterUncertainty(), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          param_ranges: ranges,
          observed: observed.split(",").map(s => Number(s.trim())),
          n_samples: nSamples,
          basin_id: "mahanadi_delta_sub_1",
          start_date: "2024-07-01",
          end_date: "2024-07-10",
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setUncertainty(data);
      }
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  return (
    <section className="panel" aria-label="Validation & uncertainty">
      <header className="panel-head">
        <h2>VALIDATION & UNCERTAINTY</h2>
        <span className="panel-sub">HYDROLOGICAL MODEL METRICS</span>
      </header>

      <div className="slider">
        <label>OBSERVED (comma-separated)<b>{observed}</b></label>
        <input type="text" value={observed} onChange={e => setObserved(e.target.value)} placeholder="10,15,20,25,30,20,15,10,5,3"/>
      </div>

      <div className="slider">
        <label>SIMULATED (comma-separated)<b>{simulated}</b></label>
        <input type="text" value={simulated} onChange={e => setSimulated(e.target.value)} placeholder="11,14,22,24,28,19,16,9,6,2"/>
      </div>

      <button className="btn-primary" disabled={loading} onClick={computeMetrics}>
        {loading ? "COMPUTING…" : "COMPUTE METRICS"}
      </button>

      {metrics && (
        <div className="sp-metrics">
          <Metric label="NSE" value={metrics.nse} digits={4}/>
          <Metric label="KGE" value={metrics.kge} digits={4}/>
          <Metric label="RMSE" value={metrics.rmse} digits={2} unit="mm"/>
          <Metric label="MAE" value={metrics.mae} digits={2} unit="mm"/>
          <Metric label="PBIAS" value={metrics.pbias} digits={2} unit="%"/>
          <Metric label="RSR" value={metrics.rsr} digits={4}/>
          <Metric label="LOG-NSE" value={metrics.log_nse} digits={4}/>
          <Metric label="CORRELATION" value={metrics.correlation} digits={4}/>
        </div>
      )}

      <hr style={{ margin: "1rem 0" }}/>

      <div className="slider">
        <label>PARAMETER RANGES (JSON)<b>{paramRanges}</b></label>
        <input type="text" value={paramRanges} onChange={e => setParamRanges(e.target.value)} placeholder='{"X1":[100,600],"X2":[0.1,3],"X3":[20,100],"X4":[1,4]}'/>
      </div>

      <div className="slider">
        <label>ENSEMBLE SIZE<b>{nSamples}</b></label>
        <input type="number" value={nSamples} onChange={e => setNSamples(Number(e.target.value))} min={10} max={500} step={10}/>
      </div>

      <button className="btn-primary" disabled={loading} onClick={runUncertainty}>
        {loading ? "RUNNING ENSEMBLE…" : "RUN PARAMETER UNCERTAINTY"}
      </button>

      {uncertainty && (
        <div className="sp-metrics">
          <Metric label="SUCCESSFUL RUNS" value={uncertainty.n_successful}/>
          <Metric label="FAILED RUNS" value={uncertainty.n_failed}/>
          <Metric label="MEAN NSE" value={uncertainty.metric_statistics?.nse?.mean} digits={4}/>
          <Metric label="MEAN KGE" value={uncertainty.metric_statistics?.kge?.mean} digits={4}/>
        </div>
      )}

      {catalog && (
        <details style={{ marginTop: "1rem" }}>
          <summary>METRICS CATALOG</summary>
          <pre style={{ fontSize: "0.75rem", overflow: "auto" }}>{JSON.stringify(catalog.metrics, null, 2)}</pre>
        </details>
      )}
    </section>
  );
}