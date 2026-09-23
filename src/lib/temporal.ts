// Temporal model for the chronological interface.
//
// The zones are derived from what the backend can actually support, not from a
// hard-coded assumption:
//
//   historical  a date inside the observation record, before the latest one
//   observed    the latest validated observation the platform holds (NOW)
//   forecast    a date after NOW, served by an explicit model contract
//   scenario    an explicit user-selected sensitivity experiment
//
// Coverage bounds come from /api/rainfall/info and NOW from /api/twin/now.
// Dates outside coverage are reported as unavailable rather than silently
// clamped, because clamping would present a different date's data as if it
// belonged to the requested one.

export type TemporalMode = "historical" | "observed" | "forecast" | "scenario";

export type Coverage = {
  start: string;
  end: string;
  variable: string;
  units: string;
  source: string;
};

/** Certainty label for the current temporal position. */
export const MODE_LABEL: Record<TemporalMode, string> = {
  historical: "OBSERVED",
  observed: "OBSERVED",
  forecast: "FORECAST",
  scenario: "SCENARIO",
};

/** Zone name used on the timeline track. */
export const MODE_ZONE: Record<TemporalMode, string> = {
  historical: "PAST",
  observed: "NOW",
  forecast: "NEXT",
  scenario: "WHAT-IF",
};

export const MODE_NOTE: Record<TemporalMode, string> = {
  historical: "Provider-backed historical observation.",
  observed: "Latest validated observation held by the platform.",
  forecast: "Model output. Not an observation.",
  scenario: "Sensitivity experiment. Not a physical simulation or a forecast.",
};

export function toDate(value: string | Date): Date {
  return value instanceof Date ? value : new Date(`${value}T00:00:00Z`);
}

export function toISODate(value: Date): string {
  return value.toISOString().slice(0, 10);
}

export function addDays(date: string, days: number): string {
  const d = toDate(date);
  d.setUTCDate(d.getUTCDate() + days);
  return toISODate(d);
}

export function diffDays(from: string, to: string): number {
  return Math.round((toDate(to).getTime() - toDate(from).getTime()) / 86400000);
}

export function clampDate(date: string, min: string, max: string): string {
  if (date < min) return min;
  if (date > max) return max;
  return date;
}

/**
 * Derive the temporal mode from the date alone. Scenario is deliberately not
 * derivable: it is an explicit user choice, so hypothetical output can never
 * appear without the user asking for it.
 */
export function modeForDate(date: string, now: string | null): TemporalMode {
  if (!now) return "historical";
  if (date > now) return "forecast";
  if (date === now) return "observed";
  return "historical";
}

/** True when the date falls inside the validated observation record. */
export function isWithinCoverage(date: string, coverage: Coverage | null): boolean {
  if (!coverage) return false;
  return date >= coverage.start && date <= coverage.end;
}

/**
 * Position of a date on a 0..1 track spanning [min, max]. Returns null for a
 * degenerate span so callers render an indeterminate track rather than
 * dividing by zero.
 */
export function trackPosition(date: string, min: string, max: string): number | null {
  const span = diffDays(min, max);
  if (span <= 0) return null;
  const offset = diffDays(min, date);
  return Math.min(1, Math.max(0, offset / span));
}

const MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

/** Human-readable date, e.g. "15 JUL 2024". */
export function formatDate(date: string): string {
  if (!date) return "NO DATA";
  const d = toDate(date);
  if (Number.isNaN(d.getTime())) return date;
  return `${String(d.getUTCDate()).padStart(2, "0")} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

export function formatMonth(date: string): string {
  const d = toDate(date);
  if (Number.isNaN(d.getTime())) return date;
  return `${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

/**
 * Zone segments for the timeline track: a contiguous observed span up to NOW,
 * then a dashed model span after it. Derived from real coverage bounds so the
 * proportions reflect the actual record rather than a fixed layout.
 */
export function buildSegments(coverage: Coverage | null, now: string | null, horizonEnd: string) {
  if (!coverage || !now) return [];
  const observedStart = coverage.start;
  const observedEnd = clampDate(now, coverage.start, coverage.end);
  const total = diffDays(observedStart, horizonEnd);
  if (total <= 0) return [];
  const observedShare = Math.max(0, Math.min(1, diffDays(observedStart, observedEnd) / total));
  return [
    { kind: "observed" as const, start: observedStart, end: observedEnd, share: observedShare },
    { kind: "model" as const, start: addDays(observedEnd, 1), end: horizonEnd, share: 1 - observedShare },
  ];
}

/** Forecast lead time in days relative to NOW. Negative means before NOW. */
export function leadTime(date: string, now: string | null): number | null {
  if (!now) return null;
  return diffDays(now, date);
}
