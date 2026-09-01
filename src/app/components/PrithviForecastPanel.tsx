"use client";

import { useCallback, useEffect, useState } from "react";

type ForecastStatus = {
  status: string;
  model: string;
  forecast_generated: boolean;
  checkpoint_present: boolean;
  input_present: boolean;
  message: string;
};

export default function PrithviForecastPanel() {
  const [status, setStatus] = useState<ForecastStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch("/api/forecast/prithvi-wxc/status", { cache: "no-store" });
      if (!response.ok) throw new Error(`Prithvi-WxC status returned HTTP ${response.status}`);
      setStatus((await response.json()) as ForecastStatus);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to read Prithvi-WxC status.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  const runForecast = async () => {
    try {
      setRunning(true);
      setError(null);
      const response = await fetch("/api/forecast/prithvi-wxc", { method: "POST" });
      const data = await response.json();
      if (!response.ok) throw new Error(data?.detail ?? `Forecast request returned HTTP ${response.status}`);
      setStatus((previous) => ({
        ...(previous ?? {
          model: "Prithvi-WxC-1.0-2300M-rollout",
          checkpoint_present: false,
          input_present: false,
          message: "",
        }),
        status: data.status ?? "UNKNOWN",
        forecast_generated: Boolean(data.forecast_generated),
        message: data.message ?? (data.blockers?.join(" ") ?? "Forecast request completed."),
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prithvi-WxC forecast failed.");
    } finally {
      setRunning(false);
      await loadStatus();
    }
  };

  const ready = status?.status === "READY_FOR_INFERENCE" || status?.status === "ready";

  return (
    <section className="panel" aria-label="Prithvi-WxC forecast">
      <div className="panel-title">PRITHVI-WxC AI FORECAST</div>
      {loading ? (
        <div className="panel-message">Checking AI forecast assets…</div>
      ) : (
        <>
          <div className="forecast-status-row">
            <span className={`status-dot ${ready ? "ready" : ""}`} />
            <strong>{status?.status ?? "UNKNOWN"}</strong>
          </div>
          <div className="forecast-model">{status?.model ?? "Prithvi-WxC-1.0-2300M-rollout"}</div>
          <div className="forecast-checks">
            <span>Checkpoint: {status?.checkpoint_present ? "READY" : "MISSING"}</span>
            <span>MERRA-2 input: {status?.input_present ? "READY" : "MISSING"}</span>
          </div>
          <p className="panel-message">{status?.message}</p>
          {error && <p className="panel-error">{error}</p>}
          <button className="primary-button" type="button" onClick={runForecast} disabled={running || !ready}>
            {running ? "RUNNING AI FORECAST…" : ready ? "RUN AI FORECAST" : "WAITING FOR MODEL ASSETS"}
          </button>
        </>
      )}
    </section>
  );
}
