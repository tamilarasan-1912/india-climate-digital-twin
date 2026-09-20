"use client";

import { useEffect, useMemo, useState } from "react";

type Props = { date: string; onDateChange: (date: string) => void };

type TimelinePoint = { date: string; rainfall_mm?: number; value?: number };

export default function GodsEyeOperations({ date, onDateChange }: Props) {
  const [mode, setMode] = useState<"LIVE" | "HISTORY" | "FORECAST" | "SIMULATE">("LIVE");
  const [ops, setOps] = useState<any>(null);
  const [timeline, setTimeline] = useState<any>(null);
  const [events, setEvents] = useState<any>(null);
  const [playing, setPlaying] = useState(false);
  const [index, setIndex] = useState(0);

  useEffect(() => {
    let alive = true;
    Promise.all([
      fetch(`/api/gods-eye/operations/${date}`, { cache: "no-store" }).then(r => r.ok ? r.json() : null).catch(() => null),
      fetch(`/api/gods-eye/events/${date}`, { cache: "no-store" }).then(r => r.ok ? r.json() : null).catch(() => null),
    ]).then(([a, b]) => { if (alive) { setOps(a); setEvents(b); } });
    return () => { alive = false; };
  }, [date]);

  useEffect(() => {
    let alive = true;
    const end = new Date(date + "T00:00:00Z");
    const start = new Date(end);
    start.setUTCDate(start.getUTCDate() - 30);
    fetch(`/api/gods-eye/timeline?start=${start.toISOString().slice(0,10)}&end=${date}&forecast_horizon=7`, { cache: "no-store" })
      .then(r => r.ok ? r.json() : null).then(v => { if (alive) setTimeline(v); }).catch(() => { if (alive) setTimeline(null); });
    return () => { alive = false; };
  }, [date]);

  const history = useMemo<TimelinePoint[]>(() => timeline?.history?.series ?? [], [timeline]);
  const forecast = useMemo<TimelinePoint[]>(() => timeline?.forecast?.forecast ?? [], [timeline]);
  const points = useMemo(() => mode === "FORECAST" ? forecast : history, [forecast, history, mode]);

  useEffect(() => {
    if (!playing || !points.length) return;
    const timer = window.setInterval(() => {
      setIndex(i => {
        const next = i + 1;
        if (next >= points.length) { setPlaying(false); return 0; }
        const p = points[next];
        if (mode !== "FORECAST" && p?.date) onDateChange(p.date);
        return next;
      });
    }, 450);
    return () => window.clearInterval(timer);
  }, [playing, points, mode, onDateChange]);

  const freshness = ops?.layers ?? [];
  const activeEvents = events?.events ?? [];

  return (
    <section className="godseye-operations">
      <div className="godseye-modebar">
        <div><span className="eyebrow">TWIN CONTROL</span><b>LIVE CLIMATE STATE</b></div>
        <div className="godseye-modes">
          {(["LIVE", "HISTORY", "FORECAST", "SIMULATE"] as const).map(x =>
            <button key={x} className={mode === x ? "active" : ""} onClick={() => { setMode(x); setIndex(0); setPlaying(false); }}>{x}</button>
          )}
        </div>
      </div>

      <div className="godseye-timeline">
        <button className="play" onClick={() => setPlaying(v => !v)} disabled={!points.length}>{playing ? "Ⅱ" : "▶"}</button>
        <div className="timeline-track">
          <input type="range" min={0} max={Math.max(0, points.length - 1)} value={Math.min(index, Math.max(0, points.length - 1))} onChange={e => {
            const i = Number(e.target.value); setIndex(i);
            const p = points[i]; if (mode !== "FORECAST" && p?.date) onDateChange(p.date);
          }} />
          <div><span>{points[0]?.date ?? "NO DATA"}</span><b>{points[index]?.date ?? date}</b><span>{points[points.length - 1]?.date ?? "NO DATA"}</span></div>
        </div>
        <div className="time-mode">{mode === "FORECAST" ? "MODEL" : mode === "HISTORY" ? "OBSERVED" : mode === "SIMULATE" ? "SCENARIO" : "LIVE"}</div>
      </div>

      <div className="godseye-status-row">
        <div><span>EVENTS</span><b>{events ? activeEvents.length : "NO DATA"}</b></div>
        <div><span>DATA LAYERS</span><b>{freshness.filter((x:any) => x.data_available).length}/{freshness.length || 0}</b></div>
        <div><span>DATE</span><b>{date}</b></div>
        <div><span>POLICY</span><b>NO FABRICATION</b></div>
      </div>

      <div className="godseye-freshness">
        {freshness.map((x:any) => <div key={x.layer} className={x.data_available ? "fresh" : "nodata"}>
          <span>{x.title}</span><b>{x.status === "connected" ? "● CONNECTED" : x.status.toUpperCase()}</b><small>{x.provider}</small>
        </div>)}
      </div>

      {mode === "SIMULATE" && <div className="godseye-scenario-note">Scenario mode is linked to the existing sensitivity experiment. It does not turn unmodeled temperature or sea-level parameters into physical predictions.</div>}
    </section>
  );
}
