"use client";

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import ClimateMap, { type MapLayerKey } from "../components/ClimateMap";
import ClimateLayerControl from "../components/ClimateLayerControl";
import LocationBreadcrumb from "../components/LocationBreadcrumb";
import TemporalModeIndicator from "../components/TemporalModeIndicator";
import TemporalTimeline from "../components/TemporalTimeline";
import { DataStatus, NoData, ProvenanceBadge } from "../components/DataStatus";
import {
  describeFailure,
  endpoints,
  getJSON,
  type AssistantPayload,
  type CoveragePayload,
  type DistrictClimatePayload,
  type EventsSummaryPayload,
  type ForecastPayload,
  type HealthPayload,
  type HistoricalPayload,
  type LayersPayload,
  type ModelsPayload,
  type NowPayload,
  type PrithviStatusPayload,
  type ProvenancePayload,
  type RainfallSummaryPayload,
  type RiskSummaryPayload,
  type ScenarioPayload,
  type StateClimatePayload,
  type StateTwinPayload,
  type SystemStatusPayload,
  type ValidationPayload,
} from "@/lib/api";
import {
  MODE_LABEL,
  MODE_ZONE,
  addDays,
  diffDays,
  formatDate,
  modeForDate,
  type Coverage,
  type TemporalMode,
} from "@/lib/temporal";
import { useResource } from "@/lib/use-resource";

// Navigation is ordered by the question being asked, following the chronological
// story: what happened, what is happening, what may happen next, what if.
const NAV: { group: string; items: { label: string; hint: string }[] }[] = [
  {
    group: "OBSERVE",
    items: [
      { label: "Overview", hint: "Current climate state" },
      { label: "Digital Twin", hint: "Fused state representation" },
      { label: "Observations", hint: "Providers and provenance" },
      { label: "Historical", hint: "Observed record" },
    ],
  },
  {
    group: "ANALYSE",
    items: [
      { label: "Climate", hint: "Variable catalog" },
      { label: "Districts", hint: "District aggregation" },
      { label: "Risk", hint: "Hazard and risk engine" },
      { label: "Extreme Events", hint: "Detected extremes" },
    ],
  },
  {
    group: "PROJECT",
    items: [
      { label: "Forecast", hint: "Model output" },
      { label: "What-If", hint: "Sensitivity experiment" },
    ],
  },
  {
    group: "TRUST",
    items: [
      { label: "Validation", hint: "Model skill" },
      { label: "Provenance", hint: "Data lineage" },
      { label: "Assistant", hint: "Climate intelligence" },
      { label: "System", hint: "Capability contract" },
    ],
  },
];

const NAV_HINT = Object.fromEntries(NAV.flatMap(g => g.items.map(i => [i.label, i.hint])));

const STATE_NAMES: Record<string, string> = {
  "tamil nadu": "IN-TN", karnataka: "IN-KA", kerala: "IN-KL", maharashtra: "IN-MH", delhi: "IN-DL",
  "west bengal": "IN-WB", "andhra pradesh": "IN-AP", telangana: "IN-TG", gujarat: "IN-GJ",
  rajasthan: "IN-RJ", odisha: "IN-OR", "uttar pradesh": "IN-UP", "madhya pradesh": "IN-MP",
  punjab: "IN-PB", bihar: "IN-BR", assam: "IN-AS", goa: "IN-GA", haryana: "IN-HR",
};

const EMPTY_LAYERS: Record<MapLayerKey, boolean> = {
  rainfall: true, temperature: false, lst: false, sst: false, anomalies: false, risk: false, events: true,
};

type TwinData = {
  health: HealthPayload | null;
  coverage: Coverage | null;
  now: NowPayload | null;
  system: SystemStatusPayload | null;
  layers: LayersPayload | null;
  variables: Record<string, unknown> | null;
  models: ModelsPayload | null;
  validation: ValidationPayload | null;
  provenance: ProvenancePayload | null;
  hierarchy: { states_and_union_territories?: { id: string; name: string }[] } | null;
  prithvi: PrithviStatusPayload | null;
  intelligence: Record<string, unknown> | null;
};

const EMPTY_TWIN: TwinData = {
  health: null, coverage: null, now: null, system: null, layers: null, variables: null,
  models: null, validation: null, provenance: null, hierarchy: null, prithvi: null, intelligence: null,
};

export default function ConsolePage() {
  const [nav, setNav] = useState("Overview");
  const [data, setData] = useState<TwinData>(EMPTY_TWIN);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Single source of temporal truth; every panel derives from it. `mode` is
  // derived from the date rather than stored, so it cannot fall out of sync when
  // the timeline moves. Scenario is the one explicit exception: it is a user
  // choice and is never inferred from a date, so hypothetical output cannot
  // appear unless it was asked for.
  const [date, setDate] = useState("2024-07-15");
  const [scenarioMode, setScenarioMode] = useState(false);
  const [layers, setLayers] = useState<Record<MapLayerKey, boolean>>(EMPTY_LAYERS);

  const [selectedId, setSelectedId] = useState("IN");
  const [selectedName, setSelectedName] = useState("INDIA");
  const [districtName, setDistrictName] = useState<string | null>(null);

  const [zoom, setZoom] = useState<{ type: "in" | "out" | "reset"; nonce: number } | null>(null);
  const [coords, setCoords] = useState("—");
  const [horizon, setHorizon] = useState(7);

  const [scenario, setScenario] = useState<ScenarioPayload | null>(null);
  const [simulating, setSimulating] = useState(false);
  const [scenarioError, setScenarioError] = useState<string | null>(null);
  const [scenarioParams, setScenarioParams] = useState({ precip: 20, temp: 2, sea: 0.4 });

  const [assistantQuestion, setAssistantQuestion] = useState("");
  const [assistantAnswer, setAssistantAnswer] = useState<AssistantPayload | null>(null);
  const [assistantBusy, setAssistantBusy] = useState(false);

  const [search, setSearch] = useState("");
  const [modal, setModal] = useState<"notifications" | "account" | "export" | null>(null);

  // Derived temporal facts. Declared before the data effects because they depend
  // on the temporal position.
  const coverage = data.coverage;
  const now = data.now?.synchronization?.observation_date ?? coverage?.end ?? null;
  // Scenario overrides the derived mode, because it is an explicit user choice.
  const dateMode = modeForDate(date, now);
  const mode: TemporalMode = scenarioMode ? "scenario" : dateMode;
  const withinCoverage = coverage ? date >= coverage.start && date <= coverage.end : false;

  // ---------------------------------------------------------------- bootstrap
  // The fetch and the state update are separate so the update can happen in a
  // promise callback rather than synchronously inside the effect body.
  const loadBootstrap = useCallback(async () => {
    const [health, coverageRes, nowRes, system, layerRes, variables, models, validation, provenance, hierarchy, prithvi, intelligence] =
      await Promise.all([
        getJSON<HealthPayload>(endpoints.health()),
        getJSON<CoveragePayload>(endpoints.coverage()),
        getJSON<NowPayload>(endpoints.now()),
        getJSON<SystemStatusPayload>(endpoints.systemStatus()),
        getJSON<LayersPayload>(endpoints.layers()),
        getJSON<Record<string, unknown>>(endpoints.variables()),
        getJSON<ModelsPayload>(endpoints.models()),
        getJSON<ValidationPayload>(endpoints.validation()),
        getJSON<ProvenancePayload>(endpoints.provenance()),
        getJSON<{ states_and_union_territories?: { id: string; name: string }[] }>(endpoints.hierarchy()),
        getJSON<PrithviStatusPayload>(endpoints.prithviStatus()),
        getJSON<Record<string, unknown>>(endpoints.intelligenceCapabilities()),
      ]);

    const coverage: Coverage | null = coverageRes.data?.time?.start && coverageRes.data?.time?.end
      ? {
          start: String(coverageRes.data.time.start).slice(0, 10),
          end: String(coverageRes.data.time.end).slice(0, 10),
          variable: coverageRes.data.variable ?? "RAINFALL",
          units: coverageRes.data.units ?? "mm",
          source: "IMD RF25",
        }
      : null;

    return {
      next: {
        health: health.data, coverage, now: nowRes.data, system: system.data, layers: layerRes.data,
        variables: variables.data, models: models.data, validation: validation.data,
        provenance: provenance.data, hierarchy: hierarchy.data, prithvi: prithvi.data,
        intelligence: intelligence.data,
      } satisfies TwinData,
      observationDate: nowRes.data?.synchronization?.observation_date ?? coverage?.end ?? null,
    };
  }, []);

  const bootstrap = useCallback(async () => {
    const { next, observationDate } = await loadBootstrap();
    setData(next);
    // NOW is the landing position: the latest validated observation the platform
    // actually holds, not today's calendar date.
    if (observationDate) setDate(observationDate);
    setLoading(false);
  }, [loadBootstrap]);

  // Refresh is the interactive path: it owns the busy indicator so the initial
  // mount does not set state synchronously from inside an effect.
  const refresh = useCallback(async () => {
    setRefreshing(true);
    await bootstrap();
    setRefreshing(false);
  }, [bootstrap]);

  useEffect(() => {
    let alive = true;
    void loadBootstrap().then(({ next, observationDate }) => {
      if (!alive) return;
      setData(next);
      if (observationDate) setDate(observationDate);
      setLoading(false);
    });
    return () => { alive = false; };
  }, [loadBootstrap]);

  // ------------------------------------------------ per-date state resources
  // Each of these is keyed by its URL, so a stale response can never be shown
  // against a newer date. See useResource.
  const rainfallRes = useResource<RainfallSummaryPayload>(endpoints.rainfallSummary(date));
  const riskRes = useResource<RiskSummaryPayload>(endpoints.riskSummary(date));
  const eventsRes = useResource<EventsSummaryPayload>(endpoints.eventsSummary(date));
  // Forecast is only requested from the model zone.
  const forecastRes = useResource<ForecastPayload>(mode === "forecast" ? endpoints.forecast(date, horizon) : null);
  const historicalRes = useResource<HistoricalPayload>(endpoints.historicalRainfall(addDays(date, -29), date));
  const stateTwinRes = useResource<StateTwinPayload>(selectedId === "IN" ? null : endpoints.stateTwin(selectedId, date));
  const stateClimateRes = useResource<StateClimatePayload>(selectedId === "IN" ? null : endpoints.stateClimate(selectedId, date));
  const districtRes = useResource<DistrictClimatePayload>(selectedId === "IN" ? null : endpoints.districts(selectedId, date));

  const rainfall = rainfallRes.data;
  const risk = riskRes.data;
  const events = eventsRes.data;
  const forecast = forecastRes.data;
  const historical = historicalRes.data;
  // A state-scoped panel must not fall back to the national twin.
  const stateTwin = selectedId === "IN" ? null : stateTwinRes.data;
  const stateClimate = selectedId === "IN" ? null : stateClimateRes.data;
  const districtData = selectedId === "IN" ? null : districtRes.data;

  // A 400 means the date is outside the validated record, which is reported as
  // unavailable rather than as a backend fault.
  const stateBusy = rainfallRes.loading;
  const stateError = !rainfallRes.loading && !rainfall
    ? describeFailure(rainfallRes.error, rainfallRes.status)
    : null;

  // ------------------------------------------------------------- interactions
  const chooseState = useCallback((name: string) => {
    const normalized = name.trim().toLowerCase();
    setDistrictName(null);
    if (normalized === "india") { setSelectedId("IN"); setSelectedName("INDIA"); return; }
    const id = STATE_NAMES[normalized];
    const found = id
      ? { id, name }
      : data.hierarchy?.states_and_union_territories?.find(s => s.name.toLowerCase() === normalized);
    if (found) {
      setSelectedId(found.id);
      setSelectedName(String(found.name).toUpperCase());
    }
  }, [data.hierarchy]);

  const doSearch = useCallback(() => {
    const q = search.trim().toLowerCase();
    if (!q) return;
    chooseState(q);
    setSearch("");
  }, [search, chooseState]);

  const toggleLayer = useCallback((key: MapLayerKey) => {
    setLayers(current => ({ ...current, [key]: !current[key] }));
  }, []);

  const runScenario = useCallback(async () => {
    setSimulating(true);
    setScenario(null);
    setScenarioError(null);
    // The engine perturbs a real observed state, so the base date must lie inside
    // the validated record. When the cursor sits in the model zone the nearest
    // observation is used, and the anchor is reported back to the user.
    const anchor = now ?? date;
    const params = new URLSearchParams({
      base_date: anchor,
      precipitation_delta_pct: String(scenarioParams.precip),
      temperature_delta_c: String(scenarioParams.temp),
      sea_level_rise_m: String(scenarioParams.sea),
      scenario: selectedName,
    });
    const res = await getJSON<ScenarioPayload>(endpoints.whatIf(params));
    setScenario(res.data);
    if (!res.data) setScenarioError(describeFailure(res.error, res.status));
    setSimulating(false);
  }, [date, now, scenarioParams, selectedName]);

  const askAssistant = useCallback(async (question?: string) => {
    const q = (question ?? assistantQuestion).trim();
    if (!q) return;
    setAssistantQuestion(q);
    setAssistantBusy(true);
    setAssistantAnswer(null);
    const res = await getJSON<AssistantPayload>(endpoints.intelligence(q, date, "rainfall"));
    setAssistantAnswer(res.data ?? { status: "UNAVAILABLE", answer: describeFailure(res.error, res.status) });
    setAssistantBusy(false);
  }, [assistantQuestion, date]);

  const exportJSON = useCallback(() => {
    const payload = {
      project: "India Climate Digital Twin",
      scope: "India",
      temporal: { date, mode, zone: MODE_ZONE[mode] },
      location: { id: selectedId, name: selectedName, district: districtName },
      twin: selectedId === "IN" ? data.now : stateTwin,
      rainfall, risk, events, forecast, scenario,
      provenance: data.provenance,
      coverage: data.coverage,
      generated: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `india-climate-twin-${selectedId}-${date}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
    setModal("export");
  }, [date, mode, selectedId, selectedName, districtName, data.now, data.provenance, data.coverage, stateTwin, rainfall, risk, events, forecast, scenario]);

  // Derived temporal facts.
  const sourceLabel = mode === "forecast"
    ? forecast?.forecast?.[0]?.model ?? "7-DAY MOVING-AVERAGE BASELINE"
    : data.now?.synchronization?.source ?? coverage?.source ?? null;

  const layerContract = data.layers?.layers ?? null;
  const districtMetricsById = useMemo(() => {
    const out: Record<string, any> = {};
    for (const d of districtData?.districts ?? []) if (d?.district_id) out[d.district_id] = d;
    return out;
  }, [districtData]);

  const apiOnline = Boolean(data.health);

  // ---------------------------------------------------------------- map block
  const map = (
    <div className="map-wrap">
      <div className="map-hud" aria-hidden="true">
        <span className="hud-scope">{selectedName === "INDIA" ? "INDIA" : `INDIA / ${selectedName}`}</span>
        <b>{formatDate(date)}</b>
        <span className={`hud-mode hud-${mode}`}>{MODE_LABEL[mode]}</span>
        {sourceLabel && <small>{sourceLabel}</small>}
      </div>

      <ClimateMap
        layers={layers}
        date={date}
        selectedState={selectedName}
        districtMetrics={districtMetricsById}
        onStateSelect={chooseState}
        onCoords={(lat: number, lon: number) => setCoords(`${lat.toFixed(4)}° N, ${lon.toFixed(4)}° E`)}
        zoomRequest={zoom ?? undefined}
      />

      <div className="map-actions">
        <button onClick={() => setZoom({ type: "in", nonce: Date.now() })} aria-label="Zoom in">+</button>
        <button onClick={() => setZoom({ type: "out", nonce: Date.now() })} aria-label="Zoom out">−</button>
        <button onClick={() => setZoom({ type: "reset", nonce: Date.now() })} aria-label="Reset view">⌂</button>
      </div>

      <div className="map-layers">
        <ClimateLayerControl layers={layers} contract={layerContract} onToggle={toggleLayer}/>
      </div>

      <div className="map-foot">
        <span className="map-coords">{coords}</span>
        <span className="map-obs">
          {withinCoverage || mode === "forecast"
            ? `${MODE_LABEL[mode]} · ${sourceLabel ?? "NO SOURCE"}`
            : "OUTSIDE OBSERVATION RECORD"}
        </span>
      </div>
    </div>
  );

  // ------------------------------------------------------------ HUD metrics
  // National rows come from the country-wide summaries. State rows come only
  // from state-scoped endpoints, so a drill-down can never display national
  // numbers under a state heading. Field names differ between the endpoints
  // (mean_rainfall_mm vs rainfall_mean_mm), so each is read explicitly.
  const atState = selectedId !== "IN";
  const stateMetrics = stateClimate?.metrics ?? stateTwin?.twin?.state_variables ?? undefined;
  const stateGrid = Number(stateClimate?.metrics?.valid_grid_cells ?? stateMetrics?.valid_grid_cells ?? NaN);

  const meanRain = atState
    ? (numberOrNull(stateMetrics?.mean_rainfall_mm))
    : (rainfall?.rainfall?.mean_mm ?? null);
  const maxRain = atState
    ? (numberOrNull(stateMetrics?.maximum_rainfall_mm))
    : (rainfall?.rainfall?.maximum_mm ?? null);
  const meanHazard = atState
    ? (numberOrNull(stateMetrics?.mean_hazard_score))
    : (risk?.statistics?.mean_hazard_score ?? null);
  const maxHazard = atState
    ? (numberOrNull(stateMetrics?.maximum_hazard_score))
    : (risk?.statistics?.maximum_hazard_score ?? null);
  const gridPoints = atState
    ? (Number.isFinite(stateGrid) ? stateGrid : null)
    : (rainfall?.grid_points ?? null);
  // Extreme-event and hazard-grid summaries are national, so they are withheld
  // for a state rather than shown against the wrong geography.
  const extremePoints = atState ? null : (events?.summary?.total_extreme_points ?? null);
  const validHazardCells = atState ? null : (risk?.grid?.valid_points ?? null);

  const statePanel = (
    <section className="panel state-panel" aria-label="Current climate state">
      <header className="panel-head">
        <h2>{selectedName === "INDIA" ? "INDIA CLIMATE STATE" : `${selectedName} CLIMATE STATE`}</h2>
        <DataStatus
          state={stateError ? "NO DATA" : (withinCoverage || mode === "forecast") ? "CONNECTED" : "NO DATA"}
          detail={stateError ?? undefined}
        />
      </header>

      {stateBusy && <p className="panel-note" aria-live="polite">LOADING CLIMATE STATE…</p>}

      <div className="sp-metrics">
        <Metric label="MEAN RAINFALL" value={meanRain} unit="mm" digits={2}/>
        <Metric label="MAX RAINFALL" value={maxRain} unit="mm" digits={2}/>
        <Metric label="MEAN HAZARD" value={meanHazard} digits={3}/>
        <Metric label="MAX HAZARD" value={maxHazard} digits={2}/>
      </div>

      <div className="sp-rows">
        <Row label="OBSERVATION DATE" value={formatDate(date)}/>
        <Row label={atState ? "STATE GRID POINTS" : "GRID POINTS"} value={gridPoints?.toLocaleString() ?? null}/>
        <Row label="EXTREME POINTS" value={extremePoints?.toLocaleString() ?? null}/>
        <Row label="VALID HAZARD CELLS" value={validHazardCells?.toLocaleString() ?? null}/>
        <Row label="RISK MODEL" value={risk?.risk_model ?? null}/>
        <Row label="DISTRICTS WITH DATA" value={districtData?.districts_with_data ?? null}/>
      </div>

      {!withinCoverage && mode !== "forecast" && (
        <NoData
          provider="IMD RF25"
          reason={coverage
            ? `The validated rainfall record covers ${formatDate(coverage.start)} to ${formatDate(coverage.end)}.`
            : "Observation coverage could not be read from the backend."}
        />
      )}

      <ProvenanceBadge
        compact
        provenance={mode === "forecast"
          ? { model: forecast?.forecast?.[0]?.model, date, validation: "BASELINE ONLY" }
          : selectedId !== "IN"
            /* A state aggregate has its own provenance; citing the national
               dataset alone would overstate what was actually computed. */
            ? provenanceFrom(stateClimate ?? stateTwin ?? null)
            : { provider: "IMD", dataset: "RF25_ind2024_rfp25.nc", variable: coverage?.variable, units: coverage?.units, date }}
      />
    </section>
  );

  // District risk categories are real per-district values, so a state shows the
  // distribution rolled up from its districts rather than the national one.
  const stateRiskDistribution = useMemo(() => {
    if (selectedId === "IN" || !districtData?.districts) return null;
    const out: Record<string, number> = {};
    for (const d of districtData.districts) {
      const key = d.risk_category ?? "no_data";
      out[key] = (out[key] ?? 0) + 1;
    }
    return Object.keys(out).length ? out : null;
  }, [selectedId, districtData]);

  const riskPanel = (
    <section className="panel" aria-label="Risk distribution">
      <header className="panel-head">
        <h2>RISK DISTRIBUTION</h2>
        <span className="panel-sub">{selectedId === "IN" ? "HAZARD COMPONENT" : "DISTRICT ROLLUP"}</span>
      </header>
      {selectedId !== "IN"
        ? stateRiskDistribution
          ? <RiskBars distribution={stateRiskDistribution}/>
          : <NoData provider="District aggregation" reason="No district risk categories for this date."/>
        : risk?.risk_distribution
          ? <RiskBars distribution={risk.risk_distribution}/>
          : <NoData provider="Risk engine" reason="No hazard distribution for this date."/>}
      {risk?.risk_model && <p className="panel-note">Model: {risk.risk_model}</p>}
    </section>
  );

  const eventsPanel = (
    <section className="panel" aria-label="Extreme events">
      <header className="panel-head">
        <h2>EXTREME EVENTS</h2>
        <span className="panel-sub">{selectedId === "IN" ? "IMD-DERIVED DETECTOR" : "NATIONAL DETECTOR"}</span>
      </header>
      {events?.summary ? (
        <>
          <div className="sp-metrics">
            <Metric label="HEAVY" value={events.summary.heavy_points}/>
            <Metric label="VERY HEAVY" value={events.summary.very_heavy_points}/>
            <Metric label="EXTREMELY HEAVY" value={events.summary.extremely_heavy_points}/>
            <Metric label="MAX RAINFALL" value={events.summary.maximum_rainfall_mm} unit="mm" digits={1}/>
          </div>
          {selectedId !== "IN" && (
            /* The detector runs over the national grid; there is no state-scoped
               event summary endpoint, so the scope is stated rather than implied. */
            <p className="panel-note">
              Detector output for the national IMD grid on this date. A state-scoped
              event summary endpoint is not implemented.
            </p>
          )}
          <p className="panel-note">
            Thresholds from the IMD-derived detector. Event classification beyond rainfall intensity
            requires a validated model and is not shown.
          </p>
        </>
      ) : <NoData provider="Extreme event detector" reason="No event summary for this date."/>}
    </section>
  );

  const forecastPanel = (
    <section className="panel" aria-label="Forecast">
      <header className="panel-head">
        <h2>FORECAST</h2>
        <div className="seg" role="group" aria-label="Forecast horizon">
          {[1, 3, 7, 14].map(h => (
            <button key={h} className={horizon === h ? "sel" : ""} onClick={() => setHorizon(h)} aria-pressed={horizon === h}>{h}D</button>
          ))}
        </div>
      </header>
      {mode !== "forecast" ? (
        <p className="panel-note">
          Move the timeline past NOW to view model output. Forecast values are never shown as observations.
        </p>
      ) : forecast?.forecast?.length ? (
        <>
          <dl className="fc-meta">
            <div><dt>MODEL</dt><dd>{forecast.forecast[0].model ?? "7-day moving-average baseline"}</dd></div>
            <div><dt>FROM</dt><dd>{forecast.from_state_date ?? "—"}</dd></div>
            <div><dt>STATUS</dt><dd>AVAILABLE</dd></div>
            <div><dt>VALIDATION</dt><dd>BASELINE ONLY</dd></div>
          </dl>
          <div className="fc-list">
            {forecast.forecast.map(f => (
              <div className="fc-row" key={f.date}>
                <span>{f.date}</span>
                <b>{typeof f.rainfall_mm === "number" ? `${f.rainfall_mm.toFixed(2)} mm` : "NO DATA"}</b>
                <em>{f.confidence ?? "not calibrated"}</em>
              </div>
            ))}
          </div>
          <p className="panel-note">
            Transparent statistical baseline (7-day moving average). Not an AI weather model, and not
            skill-validated for operational use.
          </p>
        </>
      ) : <NoData provider="Forecast model" reason="No forecast available from this temporal position."/>}
    </section>
  );

  const scenarioPanel = (
    <section className="panel" aria-label="What-if scenario">
      <header className="panel-head"><h2>WHAT-IF</h2><span className="panel-sub">SENSITIVITY EXPERIMENT</span></header>
      <p className="scenario-warn" role="status">
        SENSITIVITY EXPERIMENT — NOT A FULL PHYSICAL SIMULATION. Perturbed inputs through the existing
        hazard engine, not a climate prediction.
      </p>
      <p className="panel-note">
        Applied to the validated observation at {formatDate(now ?? date)}
        {now && date !== now ? ` (nearest observation to the selected date, ${formatDate(date)})` : ""}.
      </p>
      <Slider label="PRECIPITATION" value={scenarioParams.precip} min={-100} max={300} step={1} unit="%"
        onChange={v => setScenarioParams(s => ({ ...s, precip: v }))}/>
      <Slider label="TEMPERATURE" value={scenarioParams.temp} min={-10} max={10} step={0.5} unit="°C"
        onChange={v => setScenarioParams(s => ({ ...s, temp: v }))}/>
      <Slider label="SEA LEVEL" value={scenarioParams.sea} min={0} max={2} step={0.1} unit="m"
        onChange={v => setScenarioParams(s => ({ ...s, sea: v }))}/>
      <button className="btn-primary" disabled={simulating} onClick={runScenario}>
        {simulating ? "RUNNING…" : "RUN SENSITIVITY EXPERIMENT"}
      </button>
      {scenario ? (
        <>
          <div className="sp-metrics">
            <Metric label="MEAN HAZARD" value={scenario.scenario_result?.mean_hazard_score} digits={4}/>
            <Metric label="MAX HAZARD" value={scenario.scenario_result?.maximum_hazard_score} digits={2}/>
            <Metric label="BASELINE MEAN" value={scenario.baseline?.mean_hazard_score} digits={4}/>
            <Metric label="DELTA" value={scenario.scenario_result?.mean_score_delta} digits={4}/>
          </div>
          {/* Which parameters were actually coupled, and which were only recorded. */}
          {scenario.coupling && (
            <dl className="fc-meta">
              <div><dt>PRECIPITATION</dt><dd>{scenario.coupling.precipitation}</dd></div>
              <div><dt>TEMPERATURE</dt><dd>{scenario.coupling.temperature}</dd></div>
              <div><dt>SEA LEVEL</dt><dd>{scenario.coupling.sea_level_rise}</dd></div>
            </dl>
          )}
          <p className="scenario-warn">{scenario.scientific_status ?? scenario.warning}</p>
        </>
      ) : scenarioError ? (
        <NoData provider="Scenario engine" reason={scenarioError}/>
      ) : (
        <p className="panel-note">No scenario has been run for this position. Scenario output never replaces observed values.</p>
      )}
    </section>
  );

  // ------------------------------------------------------------- nav sections
  let body: ReactNode;
  if (nav === "Overview") {
    body = (
      <div className="overview">
        {map}
        <div className="overview-side">
          {statePanel}
          {mode === "scenario" ? scenarioPanel : mode === "forecast" ? forecastPanel : riskPanel}
        </div>
        <div className="overview-foot">{eventsPanel}</div>
      </div>
    );
  } else if (nav === "Digital Twin") {
    body = (
      <div className="split">
        {map}
        <div className="split-side">
          <section className="panel">
            <header className="panel-head"><h2>DIGITAL TWIN STATE</h2><span className="panel-sub">DETERMINISTIC REPRESENTATION</span></header>
            <p className="panel-note">
              The twin fuses provider-backed observations into a deterministic climate-state
              representation. It is not a trained neural latent space.
            </p>
            <Json data={selectedId === "IN" ? data.now : stateTwin}/>
          </section>
          {statePanel}
        </div>
      </div>
    );
  } else if (nav === "Observations") {
    body = (
      <div className="two">
        <section className="panel">
          <header className="panel-head"><h2>OBSERVATION SOURCES</h2></header>
          <div className="source-list">
            {Object.entries(data.layers?.layers ?? {}).map(([key, layer]) => (
              <div className="source-row" key={key}>
                <span className="source-name">{layer.title ?? key.toUpperCase()}</span>
                <span className="source-provider">{(layer.providers ?? []).join(", ") || "—"}</span>
                <DataStatus state={String(layer.status ?? "").toUpperCase()}/>
              </div>
            ))}
            {!data.layers && <NoData reason="Layer contract unavailable."/>}
          </div>
        </section>
        <section className="panel">
          <header className="panel-head"><h2>PROVENANCE</h2></header>
          <ProvenanceBadge provenance={provenanceFrom(data.provenance)}/>
          <Json data={data.provenance}/>
        </section>
      </div>
    );
  } else if (nav === "Historical") {
    body = (
      <div className="two">
        <section className="panel">
          <header className="panel-head"><h2>OBSERVED RECORD</h2><span className="panel-sub">30 DAYS TO {formatDate(date)}</span></header>
          {historical?.series?.length ? (
            <>
              <RainfallChart series={historical.series} now={now}/>
              <p className="panel-note">
                {historical.provider ?? "IMD"} · {historical.variable ?? "RAINFALL"} · {historical.unit ?? "mm"} ·{" "}
                {historical.count ?? 0} observations. Provider-backed observations, unmodified.
              </p>
            </>
          ) : <NoData provider="IMD RF25" reason="No observations in this window."/>}
        </section>
        <section className="panel">
          <header className="panel-head"><h2>TIME CONTROL</h2></header>
          <TemporalModeIndicator mode={mode} date={date} now={now} source={sourceLabel} horizonDays={horizon}/>
          <div className="sp-rows">
            <Row label="RECORD START" value={coverage ? formatDate(coverage.start) : null}/>
            <Row label="RECORD END" value={coverage ? formatDate(coverage.end) : null}/>
            <Row label="NOW" value={now ? formatDate(now) : null}/>
            <Row label="POSITION" value={now ? `${diffDays(now, date)} days from NOW` : null}/>
          </div>
        </section>
      </div>
    );
  } else if (nav === "Climate") {
    body = (
      <div className="two">
        <section className="panel">
          <header className="panel-head"><h2>CLIMATE VARIABLE CATALOG</h2></header>
          <Json data={data.variables}/>
        </section>
        <section className="panel">
          <header className="panel-head"><h2>CURRENT RAINFALL</h2><span className="panel-sub">{formatDate(date)}</span></header>
          {rainfall ? <Json data={rainfall}/> : <NoData provider="IMD RF25" reason={stateError ?? "No summary for this date."}/>}
        </section>
      </div>
    );
  } else if (nav === "Districts") {
    body = (
      <div className="single">
        <section className="panel">
          <header className="panel-head">
            <h2>DISTRICT CLIMATE AGGREGATION</h2>
            <span className="panel-sub">{selectedName} · {formatDate(date)}</span>
          </header>
          <DistrictPanel data={districtData} stateName={selectedName} onSelect={setDistrictName}/>
        </section>
      </div>
    );
  } else if (nav === "Risk") {
    body = (
      <div className="split">
        {map}
        <div className="split-side">
          <section className="panel">
            <header className="panel-head"><h2>HAZARD INTELLIGENCE</h2><span className="panel-sub">{formatDate(date)}</span></header>
            <div className="sp-metrics">
              <Metric label="MEAN HAZARD" value={meanHazard} digits={3}/>
              <Metric label="MAX HAZARD" value={maxHazard} digits={2}/>
              <Metric label="VALID CELLS" value={risk?.grid?.valid_points?.toLocaleString() ?? null}/>
            </div>
            <p className="panel-note">
              Risk is a function of hazard, exposure and vulnerability. Only the hazard component is
              computed here; exposure and vulnerability remain unpopulated rather than defaulted to zero.
            </p>
          </section>
          {riskPanel}
        </div>
      </div>
    );
  } else if (nav === "Extreme Events") {
    body = (
      <div className="split">
        {map}
        <div className="split-side">
          {eventsPanel}
          <section className="panel">
            <header className="panel-head">
              <h2>EVENT MONITOR</h2>
              <button className="btn-ghost" onClick={() => downloadEvents(events)}>EXPORT CSV</button>
            </header>
            <Json data={events}/>
          </section>
        </div>
      </div>
    );
  } else if (nav === "Forecast") {
    body = (
      <div className="two">
        {forecastPanel}
        <section className="panel">
          <header className="panel-head"><h2>MODEL CATALOG</h2></header>
          <Json data={data.models}/>
        </section>
      </div>
    );
  } else if (nav === "What-If") {
    body = (
      <div className="two">
        {scenarioPanel}
        <section className="panel">
          <header className="panel-head"><h2>SCENARIO OUTPUT</h2><span className="panel-sub">SENSITIVITY ONLY</span></header>
          {scenario ? <Json data={scenario}/> : <NoData reason="Run a sensitivity experiment to produce output."/>}
        </section>
      </div>
    );
  } else if (nav === "Validation") {
    body = (
      <div className="two">
        <section className="panel">
          <header className="panel-head"><h2>MODEL &amp; DATA VALIDATION</h2></header>
          <Json data={data.validation}/>
        </section>
        <section className="panel">
          <header className="panel-head"><h2>MODEL REGISTRY</h2></header>
          <Json data={data.models}/>
        </section>
      </div>
    );
  } else if (nav === "Provenance") {
    body = (
      <div className="single">
        <section className="panel">
          <header className="panel-head"><h2>DATA PROVENANCE</h2></header>
          <ProvenanceBadge provenance={provenanceFrom(data.provenance)}/>
          <Json data={data.provenance}/>
        </section>
      </div>
    );
  } else if (nav === "Assistant") {
    body = (
      <div className="two">
        <section className="panel assistant">
          <header className="panel-head">
            <h2>CLIMATE INTELLIGENCE</h2>
            <span className="panel-sub">{formatDate(date)} · {selectedName}</span>
          </header>
          <p className="panel-note">
            Answers are assembled from this platform&apos;s validated APIs. The assistant never invents
            climate values; when a variable or provider is unavailable it says so.
          </p>
          <label className="field">
            <span>ASK ABOUT THIS CLIMATE STATE</span>
            <input
              value={assistantQuestion}
              onChange={e => setAssistantQuestion(e.target.value)}
              onKeyDown={e => e.key === "Enter" && askAssistant()}
              placeholder="Which districts received the most rainfall?"
            />
          </label>
          <div className="chip-row">
            {[
              "What was rainfall in Tamil Nadu on this date?",
              "Which states had extreme rainfall?",
              "What is the current climate state?",
              "Why is temperature unavailable?",
              "Is Prithvi-WxC currently available?",
              "What forecast model is being used?",
            ].map(q => <button className="chip" key={q} onClick={() => askAssistant(q)}>{q}</button>)}
          </div>
          <div className="answer">
            <DataStatus
              state={assistantAnswer?.status ?? (assistantBusy ? "PARTIAL" : "NO DATA")}
              detail={assistantAnswer?.source}
            />
            <p>
              {assistantBusy
                ? "Querying the climate twin…"
                : assistantAnswer?.answer ?? "Ask a question about rainfall, risk, extreme events, models or provenance."}
            </p>
          </div>
        </section>
        <section className="panel">
          <header className="panel-head"><h2>ASSISTANT CAPABILITIES</h2></header>
          <Json data={data.intelligence}/>
        </section>
      </div>
    );
  } else {
    body = (
      <div className="system-grid">
        <SystemPanel data={data} refreshing={refreshing} onRefresh={refresh}/>
        <section className="panel">
          <header className="panel-head"><h2>STATUS CONTRACT</h2></header>
          <Json data={data.system}/>
        </section>
      </div>
    );
  }

  return (
    <main className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">🇮🇳</span>
          <div>
            <b>INDIA CLIMATE DIGITAL TWIN</b>
            <small>CHRONOLOGICAL CLIMATE INTELLIGENCE</small>
          </div>
        </div>

        <LocationBreadcrumb
          country="INDIA"
          stateName={selectedName}
          districtName={districtName}
          onNavigate={(level: "country" | "state") => {
            if (level === "country") { setSelectedId("IN"); setSelectedName("INDIA"); }
            setDistrictName(null);
          }}
        />

        <div className="topbar-actions">
          <div className="search">
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              onKeyDown={e => e.key === "Enter" && doSearch()}
              placeholder="Search state"
              aria-label="Search state"
            />
            <button onClick={doSearch} aria-label="Search">⌕</button>
          </div>
          <DataStatus state={apiOnline ? "CONNECTED" : "UNAVAILABLE"} detail={refreshing ? "SYNCHRONIZING" : undefined}/>
          <button className="icon" title="Synchronize" aria-label="Synchronize" onClick={refresh}>↻</button>
          <button className="icon" title="Bulletins" aria-label="Bulletins" onClick={() => setModal("notifications")}>♢</button>
          <button className="icon" title="Export state" aria-label="Export state" onClick={exportJSON}>⇩</button>
        </div>
      </header>

      <div className="layout">
        <aside className="rail" aria-label="Sections">
          {NAV.map(group => (
            <div className="rail-group" key={group.group}>
              <span className="rail-group-title">{group.group}</span>
              {group.items.map(item => (
                <button
                  key={item.label}
                  className={`rail-item${nav === item.label ? " active" : ""}`}
                  onClick={() => setNav(item.label)}
                  aria-current={nav === item.label ? "page" : undefined}
                  title={item.hint}
                >
                  {item.label}
                </button>
              ))}
            </div>
          ))}
        </aside>

        <section className="content">
          <TemporalTimeline
            date={date}
            now={now}
            coverage={coverage}
            mode={mode}
            horizonDays={horizon}
            busy={stateBusy}
            onScrub={next => { setScenarioMode(false); setDate(next); }}
            onCommit={next => { setScenarioMode(false); setDate(next); }}
          />

          <div className="content-head">
            <div className="content-title">
              <h1>{nav.toUpperCase()}</h1>
              <p>{NAV_HINT[nav] ?? ""}</p>
            </div>
            <div className="mode-toggle" role="group" aria-label="Temporal mode">
              <button
                className={mode === "historical" ? "sel" : ""}
                aria-pressed={mode === "historical"}
                onClick={() => {
                  setScenarioMode(false);
                  setNav("Historical");
                  if (now) setDate(addDays(now, -1));
                }}
              >PAST</button>
              <button
                className={mode === "forecast" ? "sel" : ""}
                aria-pressed={mode === "forecast"}
                onClick={() => {
                  setScenarioMode(false);
                  setNav("Forecast");
                  if (now) setDate(addDays(now, 1));
                }}
              >NEXT</button>
              <button
                className={mode === "scenario" ? "sel" : ""}
                aria-pressed={mode === "scenario"}
                onClick={() => { setScenarioMode(true); setNav("What-If"); }}
              >WHAT-IF</button>
            </div>
          </div>

          {loading ? (
            <div className="loading" aria-live="polite">CONTACTING BACKEND…</div>
          ) : !apiOnline ? (
            <div className="empty" role="status">
              BACKEND UNAVAILABLE — the API at the configured origin did not respond. Climate values are
              not shown because none could be verified. Check NEXT_PUBLIC_API_URL / the API service, then retry.
            </div>
          ) : (
            <div className="body">{body}</div>
          )}
        </section>
      </div>

      {modal && <Modal type={modal} onClose={() => setModal(null)} data={data} events={events} onExport={exportJSON}/>}
    </main>
  );
}

// ------------------------------------------------------------------ primitives
/** Coerces a backend numeric field, treating anything non-finite as missing. */
function numberOrNull(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

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

function RiskBars({ distribution }: { distribution: Record<string, number> }) {
  const total = Number(Object.values(distribution).reduce((a, b) => a + (Number(b) || 0), 0)) || 1;
  return (
    <div className="bars">
      {(["low", "moderate", "high", "extreme"] as const).map(k => (
        <div className="bar" key={k}>
          <span>{k.toUpperCase()}</span>
          <div><i className={`bar-${k}`} style={{ width: `${(Number(distribution[k] || 0) / total) * 100}%` }}/></div>
          <b>{distribution[k] ?? 0}</b>
        </div>
      ))}
    </div>
  );
}

/** Rainfall series as an inline bar chart. Values are observations, unmodified. */
function RainfallChart({ series, now }: { series: { date: string; rainfall_mm?: number; value?: number }[]; now: string | null }) {
  const values = series.map(p => Number(p.rainfall_mm ?? p.value ?? 0));
  const peak = Math.max(...values, 1);
  return (
    <div className="chart" role="img" aria-label={`Rainfall series, ${series.length} observations, peak ${peak.toFixed(2)} millimetres`}>
      {series.map(p => {
        const v = Number(p.rainfall_mm ?? p.value ?? 0);
        const isNow = Boolean(now && p.date === now);
        return (
          <div className={`chart-bar${isNow ? " is-now" : ""}`} key={p.date} title={`${p.date} · ${v.toFixed(2)} mm`}>
            <i style={{ height: `${(v / peak) * 100}%` }}/>
          </div>
        );
      })}
    </div>
  );
}

function DistrictPanel({ data, stateName, onSelect }: {
  data: DistrictClimatePayload | null; stateName: string; onSelect: (n: string) => void;
}) {
  if (!data) return <div className="empty">SELECT A STATE TO SEE DISTRICT-LEVEL AGGREGATION</div>;
  const all = data.districts ?? [];
  const rows = all.filter(d => d.valid_grid_cells);
  const missing = all.length - rows.length;
  const ranked = [...rows].sort((a, b) => (b.maximum_rainfall_mm ?? 0) - (a.maximum_rainfall_mm ?? 0)).slice(0, 25);
  return (
    <div>
      <div className="sp-metrics">
        <Metric label="STATE" value={stateName}/>
        <Metric label="DISTRICTS" value={data.count}/>
        <Metric label="WITH DATA" value={data.districts_with_data}/>
        <Metric label="NO GRID COVERAGE" value={missing}/>
      </div>
      {ranked.length === 0
        ? <NoData provider="IMD grid" reason="No district polygon in this state contains an IMD grid-point centre for this date."/>
        : (
          <div className="table">
            <div className="table-head">
              <span>DISTRICT</span><span>MEAN mm</span><span>MAX mm</span><span>CELLS</span><span>RISK</span>
            </div>
            {ranked.map(d => (
              <button className="table-row" key={d.district_id} onClick={() => onSelect(d.district_name ?? "")}>
                <span>{d.district_name}</span>
                <span>{d.mean_rainfall_mm?.toFixed(2)}</span>
                <span>{d.maximum_rainfall_mm?.toFixed(2)}</span>
                <span>{d.valid_grid_cells}</span>
                <span className={`risk-tag risk-${d.risk_category}`}>{String(d.risk_category ?? "—").toUpperCase()}</span>
              </button>
            ))}
          </div>
        )}
      <p className="panel-note">
        {data.aggregation_method ?? "Spatial aggregation over district polygons"} · Source {data.provenance?.source ?? "IMD RF25"} ·
        Geometry geoBoundaries ADM2 (ODbL 1.0). Districts without an intersecting grid-point centre are
        reported as NO GRID COVERAGE, never estimated.
      </p>
    </div>
  );
}

function SystemPanel({ data, refreshing, onRefresh }: { data: TwinData; refreshing: boolean; onRefresh: () => void }) {
  // The backend capability contract is the source of truth. Availability is never
  // inferred from the presence of a fetched object.
  const capabilities: Record<string, any> = data.system?.capabilities ?? {};
  const rows: [string, string][] = Object.keys(capabilities).length
    ? Object.entries(capabilities).flatMap(([name, value]: [string, any]) => {
        if (value && typeof value === "object" && !("state" in value)) {
          return Object.entries(value).map(([sub, subValue]: [string, any]) => [
            `${name} / ${sub}`,
            typeof subValue === "string" ? subValue : String(subValue?.state ?? "NO DATA"),
          ] as [string, string]);
        }
        return [[name, typeof value === "string" ? value : String(value?.state ?? "NO DATA")] as [string, string]];
      })
    : [
        ["API", data.health ? "CONNECTED" : "UNAVAILABLE"],
        ["IMD Rainfall", data.coverage ? "CONNECTED" : "NO DATA"],
        ["Climate Providers", data.layers ? "AVAILABLE" : "NO DATA"],
        ["Twin Engine", data.now ? "AVAILABLE" : "NO DATA"],
        ["Prithvi-WxC", String(data.prithvi?.status ?? "NO DATA").toUpperCase()],
        ["Validation", data.validation ? "AVAILABLE" : "NO DATA"],
      ];
  return (
    <section className="panel">
      <header className="panel-head">
        <h2>SYSTEM DIAGNOSTICS</h2>
        <button className="btn-ghost" onClick={onRefresh}>{refreshing ? "SYNCING" : "REFRESH"}</button>
      </header>
      <div className="service-list">
        {rows.map(([name, state]) => (
          <div className="service" key={name}>
            <span>{name}</span>
            <DataStatus state={state}/>
          </div>
        ))}
      </div>
      <p className="panel-note">
        {data.system?.policy ?? "Capability state is derived from observed data and model availability, not from configuration."}
      </p>
    </section>
  );
}

function Modal({ type, onClose, data, events, onExport }: {
  type: "notifications" | "account" | "export"; onClose: () => void; data: TwinData;
  events: EventsSummaryPayload | null; onExport: () => void;
}) {
  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} role="dialog" aria-modal="true">
        <button className="close" onClick={onClose} aria-label="Close">×</button>
        {type === "notifications" ? (
          <>
            <h2>ACTIVE BULLETINS</h2>
            <p>Derived from the connected extreme-event service. Detector output, not official warnings.</p>
            <DataStatus
              state={events ? "AVAILABLE" : "NO DATA"}
              detail={events ? `${events.summary?.total_extreme_points ?? 0} EXTREME POINTS` : undefined}
            />
          </>
        ) : type === "account" ? (
          <>
            <h2>SYSTEM PROFILE</h2>
            <div className="sp-rows">
              <Row label="SCOPE" value="INDIA"/>
              <Row label="FRONTEND" value="Next.js / MapLibre GL"/>
              <Row label="BACKEND" value="FastAPI"/>
              <Row label="API" value={data.health ? "CONNECTED" : "UNAVAILABLE"}/>
            </div>
          </>
        ) : (
          <>
            <h2>EXPORT READY</h2>
            <p>The current temporal and geographic state was exported as JSON.</p>
            <button className="btn-primary" onClick={onExport}>EXPORT AGAIN</button>
          </>
        )}
      </div>
    </div>
  );
}

function Json({ data }: { data: unknown }) {
  if (data === null || data === undefined) return <div className="empty">NO DATA</div>;
  return <pre className="json">{JSON.stringify(data, null, 2)}</pre>;
}

/** Best-effort mapping of backend provenance shapes onto the badge fields. */
function provenanceFrom(payload: ProvenancePayload | null) {
  if (!payload) return null;
  const flat: Record<string, unknown> = { ...payload };
  for (const value of Object.values(payload)) {
    if (value && typeof value === "object" && !Array.isArray(value)) Object.assign(flat, value);
  }
  const pick = (...keys: string[]) => {
    for (const key of keys) {
      const v = flat[key];
      if (typeof v === "string" && v) return v;
    }
    return undefined;
  };
  return {
    provider: pick("provider", "source", "source_provider"),
    dataset: pick("dataset", "file", "dataset_id"),
    variable: pick("variable", "source_variable"),
    units: pick("units", "unit"),
    date: pick("date", "observation_date"),
    processing: pick("processing", "method", "processing_method"),
    model: pick("model", "model_name"),
    version: pick("version", "engine_version"),
    validation: pick("validation", "status", "validation_status"),
    retrieved: pick("retrieved", "retrieved_at", "retrieval_time"),
  };
}

function downloadEvents(events: EventsSummaryPayload | null) {
  if (!events?.summary) return;
  const header = "date,total_extreme_points,heavy_points,very_heavy_points,extremely_heavy_points,maximum_rainfall_mm";
  const row = [
    events.date ?? "", events.summary.total_extreme_points ?? "", events.summary.heavy_points ?? "",
    events.summary.very_heavy_points ?? "", events.summary.extremely_heavy_points ?? "",
    events.summary.maximum_rainfall_mm ?? "",
  ].join(",");
  const blob = new Blob([[header, row].join("\n")], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `extreme-events-${events.date ?? "unknown"}.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}
