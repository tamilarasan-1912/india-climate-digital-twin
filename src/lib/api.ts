// Typed access to the climate twin API.
//
// Two rules this module exists to enforce:
//
// 1. A request always settles. The backend is a separate origin, so an
//    unreachable host can leave a fetch pending indefinitely; every call is
//    bounded by a timeout.
// 2. A superseded request is cancelled. Timeline scrubbing issues a request per
//    date, and without cancellation a slow early response could land after a
//    newer one and overwrite it with stale data.

const DEFAULT_TIMEOUT_MS = 15000;

export type ApiResult<T> = {
  data: T | null;
  status: number | null;
  error: string | null;
};

/** Fetch JSON, returning a settled result instead of throwing. */
export async function getJSON<T>(
  url: string,
  options: { signal?: AbortSignal; timeoutMs?: number } = {},
): Promise<ApiResult<T>> {
  // Everything is inside the try: constructing the abort signals can itself
  // throw on a runtime without AbortSignal.timeout/any, and that must surface as
  // a failed request rather than a rejected promise the caller cannot see.
  try {
    const timeout = AbortSignal.timeout(options.timeoutMs ?? DEFAULT_TIMEOUT_MS);
    const signal = options.signal && AbortSignal.any
      ? AbortSignal.any([options.signal, timeout])
      : options.signal ?? timeout;

    const response = await fetch(url, { cache: "no-store", signal });
    if (!response.ok) {
      // The backend distinguishes 400 (bad input), 404 (not found) and 503
      // (provider unavailable); the detail is surfaced so the UI can explain
      // which of those applies rather than showing a generic failure.
      let detail: string | null = null;
      try {
        const body = await response.json();
        detail = typeof body?.detail === "string" ? body.detail : null;
      } catch { /* non-JSON error body */ }
      return { data: null, status: response.status, error: detail ?? `HTTP ${response.status}` };
    }
    return { data: (await response.json()) as T, status: response.status, error: null };
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      return { data: null, status: null, error: "aborted" };
    }
    if (error instanceof DOMException && error.name === "TimeoutError") {
      return { data: null, status: null, error: "timeout" };
    }
    return { data: null, status: null, error: error instanceof Error ? error.message : "network error" };
  }
}

/** Human-readable explanation for a failed request, used in status panels. */
export function describeFailure(error: string | null, status: number | null): string {
  if (error === "aborted") return "Request superseded by a newer one.";
  if (error === "timeout") return "Backend did not respond in time.";
  if (status === 400) return "Requested date is outside the validated observation record.";
  if (status === 404) return "Not found.";
  if (status === 429) return "Rate limit exceeded.";
  if (status === 503) return "Required provider or model is unavailable.";
  if (status !== null && status >= 500) return "Backend error.";
  return error ?? "Unavailable.";
}

export type HealthPayload = {
  status: string;
  checks?: Record<string, boolean>;
};

export type CoveragePayload = {
  variable?: string;
  units?: string;
  time?: { start?: string; end?: string };
};

export type NowPayload = {
  synchronization?: {
    status?: string;
    observation_date?: string;
    source?: string;
    unit?: string;
    observation_count?: number;
  };
  what_now?: Record<string, unknown>;
};

export type TimelinePayload = {
  contract?: string;
  history?: { provider?: string; unit?: string; count?: number; series?: { date: string; rainfall_mm: number }[] };
  forecast?: { status?: string; source?: string; window_days?: number; horizon_days?: number; confidence?: string; forecast?: { date: string; rainfall_mm: number; model?: string }[] };
  policy?: string;
};

export type RainfallSummaryPayload = {
  date?: string;
  rainfall?: { minimum_mm?: number; maximum_mm?: number; mean_mm?: number; median_mm?: number };
  grid_points?: number;
};

export type RiskSummaryPayload = {
  statistics?: { mean_hazard_score?: number; maximum_hazard_score?: number };
  risk_distribution?: Record<string, number>;
  risk_model?: string;
  grid?: { valid_points?: number };
};

export type EventsSummaryPayload = {
  date?: string;
  summary?: {
    total_extreme_points?: number;
    heavy_points?: number;
    very_heavy_points?: number;
    extremely_heavy_points?: number;
    maximum_rainfall_mm?: number;
  };
};

export type LayersPayload = {
  scope?: string;
  layers?: Record<string, {
    title?: string;
    variables?: string[];
    providers?: string[];
    status?: string;
    endpoint?: string;
    visualization?: string;
  }>;
};

export type ForecastPayload = {
  status?: string;
  from_state_date?: string;
  horizon_days?: number;
  forecast?: { date: string; rainfall_mm: number; model?: string; confidence?: string }[];
};

export type ScenarioPayload = {
  status?: string;
  scenario?: string;
  base_date?: string;
  parameters?: { precipitation_delta_pct?: number; temperature_delta_c?: number; sea_level_rise_m?: number };
  baseline?: { mean_hazard_score?: number; maximum_hazard_score?: number };
  screening_result?: {
    mean_hazard_score?: number | null;
    maximum_hazard_score?: number | null;
    risk_distribution?: Record<string, number>;
  };
  scenario_result?: {
    mean_hazard_score?: number;
    maximum_hazard_score?: number;
    risk_distribution?: Record<string, number>;
    mean_score_delta?: number;
  };
  coupling?: { precipitation?: string; temperature?: string; sea_level_rise?: string };
  modeled_effect?: string;
  unmodeled_parameters?: string[];
  warning?: string;
  scientific_status?: string;
};

export type AssistantPayload = {
  answer?: string;
  status?: string;
  data_available?: boolean;
  source?: string;
  date?: string;
  layer?: string;
  question?: string;
};

export type ProvenancePayload = Record<string, unknown>;

export type SystemStatusPayload = {
  policy?: string;
  capabilities?: Record<string, { state?: string; [key: string]: unknown } | string>;
};

export type PrithviStatusPayload = {
  model?: string;
  status?: string;
  checkpoint?: { present?: boolean; expected_size_gb?: number; note?: string };
  blocking_reasons?: string[];
  [key: string]: unknown;
};

export type ModelsPayload = Record<string, unknown>;

export type ValidationPayload = Record<string, unknown>;

export type StateClimatePayload = {
  status?: string;
  state_id?: string;
  state_name?: string;
  observation_date?: string;
  variable?: string;
  units?: string;
  metrics?: Record<string, number | string | null>;
  data_coverage?: Record<string, unknown>;
  provenance?: Record<string, unknown>;
};

export type StateTwinPayload = {
  twin?: {
    state_variables?: Record<string, unknown>;
    state_name?: string;
    state_id?: string;
    observation_date?: string;
    provenance?: Record<string, unknown>;
    aggregation?: Record<string, unknown>;
    status?: string;
  };
  state_variables?: Record<string, unknown>;
  status?: string;
  provenance?: Record<string, unknown>;
};

export type DistrictClimatePayload = {
  count?: number;
  districts_with_data?: number;
  aggregation_method?: string;
  provenance?: { source?: string };
  districts?: {
    district_id?: string;
    district_name?: string;
    valid_grid_cells?: number;
    mean_rainfall_mm?: number;
    maximum_rainfall_mm?: number;
    risk_category?: string;
  }[];
};

export type HistoricalPayload = {
  variable?: string;
  unit?: string;
  provider?: string;
  count?: number;
  series?: { date: string; rainfall_mm?: number; value?: number }[];
};

/** Every endpoint the console reads, as path builders so dates stay in one place. */
export const endpoints = {
  health: () => "/api/health",
  ready: () => "/api/ready",
  coverage: () => "/api/rainfall/info",
  now: () => "/api/twin/now",
  systemStatus: () => "/api/system/status",
  layers: () => "/api/climate/layers",
  variables: () => "/api/climate/variables",
  models: () => "/api/models",
  validation: () => "/api/validation",
  provenance: () => "/api/provenance",
  hierarchy: () => "/api/india/hierarchy",
  prithviStatus: () => "/api/ai/prithvi/status",
  intelligenceCapabilities: () => "/api/climate/intelligence/capabilities",
  timeline: (start: string, end: string, horizon: number) =>
    `/api/gods-eye/timeline?start=${start}&end=${end}&forecast_horizon=${horizon}`,
  godsEyeState: (date: string) => `/api/gods-eye/state?date=${date}`,
  operations: (date: string) => `/api/gods-eye/operations/${date}`,
  rainfallSummary: (date: string) => `/api/rainfall/summary/${date}`,
  riskSummary: (date: string) => `/api/risk/summary/${date}`,
  eventsSummary: (date: string) => `/api/extreme-events/summary/${date}`,
  twinSummary: (date: string) => `/api/twin/summary?date=${date}`,
  stateTwin: (stateId: string, date: string) => `/api/india/state/${stateId}/twin/${date}`,
  stateClimate: (stateId: string, date: string) => `/api/india/state/${stateId}/climate/${date}`,
  districts: (stateId: string, date: string) => `/api/india/state/${stateId}/districts/climate/${date}`,
  forecast: (date: string, horizon: number) => `/api/twin/next?date=${date}&horizon=${horizon}`,
  historicalRainfall: (start: string, end: string) =>
    `/api/historical/rainfall?start=${start}&end=${end}&limit=400`,
  whatIf: (params: URLSearchParams) => `/api/twin/what-if?${params}`,
  intelligence: (question: string, date: string, layer: string) =>
    `/api/climate/intelligence?${new URLSearchParams({ question, date, layer })}`,
};
