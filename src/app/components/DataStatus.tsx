"use client";

import { memo } from "react";

/**
 * Capability states the backend can report. Kept as a closed set so an unknown
 * string is surfaced rather than silently rendered as healthy.
 */
export type CapabilityState =
  | "CONNECTED"
  | "AVAILABLE"
  | "DEGRADED"
  | "NO DATA"
  | "PROVIDER REQUIRED"
  | "BLOCKED"
  | "VALIDATION REQUIRED"
  | "PARTIAL"
  | "UNAVAILABLE"
  | string;

const TONE: Record<string, "ok" | "warn" | "bad" | "muted"> = {
  CONNECTED: "ok",
  AVAILABLE: "ok",
  PARTIAL: "warn",
  DEGRADED: "warn",
  "VALIDATION REQUIRED": "warn",
  "PROVIDER REQUIRED": "warn",
  BLOCKED: "bad",
  UNAVAILABLE: "bad",
  "NO DATA": "muted",
};

export function toneFor(state: CapabilityState): "ok" | "warn" | "bad" | "muted" {
  const key = String(state ?? "").toUpperCase();
  if (TONE[key]) return TONE[key];
  if (key.startsWith("CONNECTED") || key.startsWith("AVAILABLE")) return "ok";
  if (key.startsWith("PROVIDER") || key.startsWith("VALIDATION") || key.startsWith("PARTIAL")) return "warn";
  if (key.startsWith("BLOCKED") || key.startsWith("UNAVAILABLE")) return "bad";
  return "muted";
}

/** Inline status chip. Colour is derived from the state, never set by hand. */
export const DataStatus = memo(function DataStatus({ state, detail }: { state: CapabilityState; detail?: string }) {
  return (
    <span className={`ds ds-${toneFor(state)}`}>
      <i aria-hidden="true" />
      <span className="ds-state">{state ?? "NO DATA"}</span>
      {detail && <em className="ds-detail">{detail}</em>}
    </span>
  );
});

/**
 * A value that has no validated source. Used instead of printing 0, which would
 * be read as a measurement.
 */
export const NoData = memo(function NoData({ reason, provider }: { reason?: string; provider?: string }) {
  return (
    <div className="nodata">
      <span className="nodata-value">NO VALIDATED DATA</span>
      {provider && <span className="nodata-provider">Provider required: {provider}</span>}
      {reason && <span className="nodata-reason">{reason}</span>}
    </div>
  );
});

type Provenance = {
  provider?: string;
  dataset?: string;
  variable?: string;
  date?: string;
  units?: string;
  processing?: string;
  model?: string;
  version?: string;
  validation?: string;
  retrieved?: string;
  resolution?: string;
};

/**
 * Provenance badge: answers "where did this number come from". Only the fields
 * the backend actually supplies are rendered.
 */
export const ProvenanceBadge = memo(function ProvenanceBadge({ provenance, compact }: { provenance: Provenance | null; compact?: boolean }) {
  if (!provenance || Object.values(provenance).every(v => v === undefined || v === null || v === "")) {
    return <span className="prov prov-empty">PROVENANCE NOT REPORTED</span>;
  }
  const rows: [string, string | undefined][] = [
    ["Provider", provenance.provider],
    ["Dataset", provenance.dataset],
    ["Variable", provenance.variable],
    ["Units", provenance.units],
    ["Date", provenance.date],
    ["Resolution", provenance.resolution],
    ["Processing", provenance.processing],
    ["Model", provenance.model],
    ["Version", provenance.version],
    ["Validation", provenance.validation],
    ["Retrieved", provenance.retrieved],
  ];
  const shown = rows.filter(([, v]) => v !== undefined && v !== null && v !== "");
  if (compact) {
    return (
      <span className="prov prov-compact">
        {shown.slice(0, 3).map(([k, v]) => <span key={k}><b>{k}</b> {v}</span>)}
      </span>
    );
  }
  return (
    <dl className="prov">
      {shown.map(([k, v]) => <div key={k}><dt>{k.toUpperCase()}</dt><dd>{v}</dd></div>)}
    </dl>
  );
});
