"use client";

import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  MODE_ZONE,
  buildSegments,
  clampDate,
  diffDays,
  formatDate,
  formatMonth,
  trackPosition,
  type Coverage,
  type TemporalMode,
} from "@/lib/temporal";

type Props = {
  date: string;
  now: string | null;
  coverage: Coverage | null;
  mode: TemporalMode;
  horizonDays: number;
  busy: boolean;
  onScrub: (date: string) => void;
  onCommit: (date: string) => void;
};

/**
 * The timeline is the backbone of the interface: moving it changes the climate
 * state everywhere else.
 *
 * Scrubbing and committing are separate. Dragging calls onScrub on every frame
 * so the indicator tracks the pointer, while onCommit fires only when the
 * gesture settles, which is what triggers network requests. Without that split a
 * drag would issue one request per pixel.
 */
function TemporalTimeline({ date, now, coverage, mode, horizonDays, busy, onScrub, onCommit }: Props) {
  const trackRef = useRef<HTMLDivElement | null>(null);
  const [dragging, setDragging] = useState(false);
  const [playback, setPlayback] = useState<{ playing: boolean; speed: number }>({ playing: false, speed: 1 });

  const bounds = useMemo(() => {
    if (!coverage) return null;
    // The model zone extends past the last observation so forecast and observed
    // positions share one axis. It starts after the record, never inside it.
    return {
      start: coverage.start,
      observedEnd: coverage.end,
      horizonEnd: addDaysSafe(coverage.end, Math.max(1, horizonDays)),
    };
  }, [coverage, horizonDays]);

  const segments = useMemo(
    () => buildSegments(coverage, now, bounds?.horizonEnd ?? ""),
    [coverage, now, bounds],
  );

  const position = bounds ? trackPosition(date, bounds.start, bounds.horizonEnd) : null;

  const dateFromClientX = useCallback((clientX: number): string | null => {
    const el = trackRef.current;
    if (!el || !bounds) return null;
    const rect = el.getBoundingClientRect();
    if (rect.width <= 0) return null;
    const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
    const span = diffDays(bounds.start, bounds.horizonEnd);
    return addDaysSafe(bounds.start, Math.round(ratio * span));
  }, [bounds]);

  // Pointer capture keeps the gesture alive when the pointer leaves the track.
  const handlePointerDown = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    if (!bounds) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    setDragging(true);
    setPlayback(p => ({ ...p, playing: false }));
    const next = dateFromClientX(event.clientX);
    if (next) onScrub(next);
  }, [bounds, dateFromClientX, onScrub]);

  const handlePointerMove = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    if (!dragging) return;
    const next = dateFromClientX(event.clientX);
    if (next) onScrub(next);
  }, [dragging, dateFromClientX, onScrub]);

  const handlePointerUp = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    if (!dragging) return;
    setDragging(false);
    const next = dateFromClientX(event.clientX);
    if (next) onCommit(next);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }, [dragging, dateFromClientX, onCommit]);

  const step = useCallback((days: number) => {
    if (!bounds) return;
    onCommit(clampDate(addDaysSafe(date, days), bounds.start, bounds.horizonEnd));
  }, [bounds, date, onCommit]);

  const handleKeyDown = useCallback((event: React.KeyboardEvent<HTMLDivElement>) => {
    const jump = event.shiftKey ? 7 : 1;
    if (event.key === "ArrowLeft") { event.preventDefault(); step(-jump); }
    else if (event.key === "ArrowRight") { event.preventDefault(); step(jump); }
    else if (event.key === "Home" && bounds) { event.preventDefault(); onCommit(bounds.start); }
    else if (event.key === "End" && bounds) { event.preventDefault(); onCommit(bounds.horizonEnd); }
    else if (event.key === " " || event.key === "Enter") { event.preventDefault(); setPlayback(p => ({ ...p, playing: !p.playing })); }
  }, [bounds, step, onCommit]);

  // Playback advances only through the observed record: stepping into the model
  // zone would animate a forecast as if it were a sequence of observations.
  useEffect(() => {
    if (!playback.playing || !bounds || !now) return;
    const interval = window.setInterval(() => {
      const next = addDaysSafe(date, 1);
      if (next > now) { setPlayback(p => ({ ...p, playing: false })); return; }
      onCommit(next);
    }, 900 / playback.speed);
    return () => window.clearInterval(interval);
  }, [playback.playing, playback.speed, bounds, now, date, onCommit]);

  const observedEnd = bounds?.observedEnd;
  const nowPosition = now && bounds ? trackPosition(now, bounds.start, bounds.horizonEnd) : null;
  const forecastDays = now && date > now ? diffDays(now, date) : null;

  return (
    <section className="tl" aria-label="Climate timeline">
      <div className="tl-head">
        <div className="tl-when">
          <span className="tl-eyebrow">WHEN</span>
          <strong>{formatDate(date)}</strong>
          <em className={`tl-zone zone-${mode}`}>{MODE_ZONE[mode]}</em>
        </div>
        <div className="tl-playback">
          <button
            className="tl-play"
            onClick={() => setPlayback(p => ({ ...p, playing: !p.playing }))}
            disabled={!bounds}
            aria-label={playback.playing ? "Pause playback" : "Play observations"}
          >
            {playback.playing ? "❚❚" : "▶"}
          </button>
          <div className="tl-speed" role="group" aria-label="Playback speed">
            {[0.5, 1, 2].map(s => (
              <button
                key={s}
                className={playback.speed === s ? "sel" : ""}
                onClick={() => setPlayback(p => ({ ...p, speed: s }))}
                aria-pressed={playback.speed === s}
              >
                {s}×
              </button>
            ))}
          </div>
        </div>
      </div>

      <div
        ref={trackRef}
        className={`tl-track${dragging ? " dragging" : ""}`}
        role="slider"
        tabIndex={0}
        aria-label="Observation date"
        aria-valuemin={bounds ? Date.parse(bounds.start) : undefined}
        aria-valuemax={bounds ? Date.parse(bounds.horizonEnd) : undefined}
        aria-valuenow={Date.parse(`${date}T00:00:00Z`)}
        aria-valuetext={formatDate(date)}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onKeyDown={handleKeyDown}
      >
        {bounds && segments.length > 0 ? (
          <div className="tl-segments">
            {segments.map(seg => (
              <div
                key={seg.kind}
                className={`tl-segment seg-${seg.kind}`}
                style={{ width: `${seg.share * 100}%` }}
                title={seg.kind === "observed"
                  ? `Observed record ${seg.start} → ${seg.end}`
                  : `Model zone ${seg.start} → ${seg.end}`}
              />
            ))}
          </div>
        ) : (
          <div className="tl-segments empty"><div className="tl-segment seg-unknown" style={{ width: "100%" }}/></div>
        )}

        {nowPosition !== null && (
          <div className="tl-now" style={{ left: `${nowPosition * 100}%` }} aria-hidden="true">
            <span>NOW</span>
          </div>
        )}

        {position !== null && (
          <div className={`tl-cursor mode-${mode}`} style={{ left: `${position * 100}%` }}>
            <i />
            <b>{formatDate(date)}</b>
            {forecastDays !== null && <em>+{forecastDays}D</em>}
          </div>
        )}
      </div>

      <div className="tl-legend">
        <span className="tl-bound">{bounds ? formatMonth(bounds.start) : "COVERAGE UNKNOWN"}</span>
        <span className="tl-key">
          <i className="key-observed"/>OBSERVED
          <i className="key-model"/>MODEL
          {mode === "scenario" && <><i className="key-scenario"/>SCENARIO</>}
        </span>
        <span className="tl-bound">{bounds ? formatMonth(bounds.horizonEnd) : "—"}</span>
      </div>

      {coverage && date > coverage.end && (
        <p className="tl-warn" role="status">
          {formatDate(date)} is beyond the validated observation record, which ends {formatDate(coverage.end)}.{" "}
          {/* Each zone states what it actually holds. Scenario is neither an
              observation nor model output, and must never be described as one. */}
          {mode === "scenario"
            ? "Scenario output is shown. It is a sensitivity experiment, not a prediction."
            : mode === "forecast"
              ? "Values shown here are model output, not observations."
              : "No observation exists for this date."}
        </p>
      )}
      {!coverage && (
        <p className="tl-warn" role="status">
          Observation coverage could not be read from the backend, so the track is shown without bounds.
        </p>
      )}
      <p className="tl-status" aria-live="polite">
        {busy ? "LOADING CLIMATE STATE…" : `OBSERVATION DATE ${formatDate(date)}${observedEnd ? ` · RECORD ENDS ${formatDate(observedEnd)}` : ""}`}
      </p>
    </section>
  );
}

/** Local date arithmetic so the component does not depend on the module's helpers. */
function addDaysSafe(date: string, days: number): string {
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export default memo(TemporalTimeline);
