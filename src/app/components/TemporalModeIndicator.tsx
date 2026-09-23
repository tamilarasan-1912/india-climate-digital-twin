"use client";

import { memo } from "react";
import { MODE_LABEL, MODE_NOTE, formatDate, leadTime, type TemporalMode } from "@/lib/temporal";

type Props = {
  mode: TemporalMode;
  date: string;
  now: string | null;
  source: string | null;
  horizonDays: number;
};

/**
 * The certainty indicator. Every climate value in this interface is one of four
 * things, and this states which one applies at the current temporal position so
 * model output is never mistaken for an observation.
 */
function TemporalModeIndicator({ mode, date, now, source, horizonDays }: Props) {
  const lead = leadTime(date, now);
  const stages: { key: TemporalMode; label: string }[] = [
    { key: "historical", label: "OBSERVED" },
    { key: "observed", label: "NOW" },
    { key: "forecast", label: "FORECAST" },
    { key: "scenario", label: "SCENARIO" },
  ];
  const activeIndex = stages.findIndex(s => s.key === mode);

  return (
    <div className={`mode-ind mode-${mode}`}>
      <div className="mode-head">
        <span className="mode-badge">{MODE_LABEL[mode]}</span>
        <span className="mode-date">{formatDate(date)}</span>
      </div>
      <div className="mode-chain" aria-hidden="true">
        {stages.map((stage, i) => (
          <span
            key={stage.key}
            className={`mode-step${i <= activeIndex ? " on" : ""}${stage.key === "forecast" || stage.key === "scenario" ? " dashed" : ""}`}
          >
            {stage.label}
          </span>
        ))}
      </div>
      <dl className="mode-meta">
        <div><dt>SOURCE</dt><dd>{source ?? "NO DATA"}</dd></div>
        <div><dt>STATUS</dt><dd>{MODE_LABEL[mode]}</dd></div>
        {mode === "forecast" && (
          <div><dt>HORIZON</dt><dd>{lead !== null ? `+${lead}D / ${horizonDays}D` : "—"}</dd></div>
        )}
      </dl>
      <p className="mode-note">{MODE_NOTE[mode]}</p>
    </div>
  );
}

export default memo(TemporalModeIndicator);
