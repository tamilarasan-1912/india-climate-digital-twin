"use client";

import { memo } from "react";
import type { MapLayerKey } from "./ClimateMap";

type LayerInfo = { status?: string; providers?: string[]; title?: string };

type Props = {
  layers: Record<MapLayerKey, boolean>;
  contract: Record<string, LayerInfo> | null;
  onToggle: (key: MapLayerKey) => void;
};

const OBSERVATION_LAYERS: MapLayerKey[] = ["rainfall", "temperature", "lst", "sst", "anomalies"];
const HAZARD_LAYERS: MapLayerKey[] = ["risk", "events"];

const LABEL: Record<MapLayerKey, string> = {
  rainfall: "RAINFALL",
  temperature: "TEMPERATURE",
  lst: "LAND SURFACE TEMP",
  sst: "SEA SURFACE TEMP",
  anomalies: "ANOMALIES",
  risk: "RISK",
  events: "EXTREME EVENTS",
};

/** Availability comes from the backend contract, never from the toggle's own state. */
function availability(contract: Record<string, LayerInfo> | null, key: MapLayerKey) {
  const status = String(contract?.[key]?.status ?? "").toLowerCase();
  if (!status) return { known: false, connected: false, status: "", providers: "" };
  return {
    known: true,
    connected: status === "connected",
    status: status.replaceAll("_", " ").toUpperCase(),
    providers: (contract?.[key]?.providers ?? []).join(", "),
  };
}

function ClimateLayerControl({ layers, contract, onToggle }: Props) {
  const row = (key: MapLayerKey) => {
    const info = availability(contract, key);
    const on = layers[key];
    const unavailable = info.known && !info.connected;
    return (
      <button
        key={key}
        className={`layer-row${on ? " on" : ""}${unavailable ? " unavailable" : ""}`}
        aria-pressed={on}
        onClick={() => onToggle(key)}
        title={unavailable ? `${info.status} — no validated provider data` : `Toggle ${LABEL[key]}`}
      >
        <span className="layer-dot" aria-hidden="true" />
        <span className="layer-name">{LABEL[key]}</span>
        {unavailable && <em className="layer-state">{info.status}</em>}
      </button>
    );
  };

  const unavailableOn = ([...OBSERVATION_LAYERS, ...HAZARD_LAYERS] as MapLayerKey[])
    .filter(k => layers[k] && !availability(contract, k).connected && availability(contract, k).known);

  return (
    <div className="layer-ctl">
      <div className="layer-group">
        <span className="layer-group-title">CLIMATE LAYERS</span>
        {OBSERVATION_LAYERS.map(row)}
      </div>
      <div className="layer-group">
        <span className="layer-group-title">HAZARDS</span>
        {HAZARD_LAYERS.map(row)}
      </div>
      {unavailableOn.length > 0 && (
        <p className="layer-note" role="status">
          {unavailableOn.map(k => LABEL[k]).join(", ")} has no validated provider. The toggle is
          shown for transparency; nothing is estimated or drawn.
        </p>
      )}
    </div>
  );
}

export default memo(ClimateLayerControl);
