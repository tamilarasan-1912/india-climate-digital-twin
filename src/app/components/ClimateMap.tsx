"use client";

import { useEffect, useRef } from "react";
import { Map, NavigationControl, Popup } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

type Props = {
  layers: { satellite: boolean; terrain: boolean; anomalies: boolean; risk: boolean; events: boolean };
  onStateSelect?: (name: string) => void;
  onCoords?: (lat: number, lon: number) => void;
  zoomRequest?: { type: "in" | "out" | "reset"; nonce: number };
};

const INDIA = "/data/india/india-states.geojson";
const DATE = "2024-07-15";

export default function ClimateMap({ layers, onStateSelect, onCoords, zoomRequest }: Props) {
  const el = useRef<HTMLDivElement | null>(null);
  const map = useRef<Map | null>(null);
  const latestLayers = useRef(layers);
  const stateCb = useRef(onStateSelect);
  const coordCb = useRef(onCoords);

  useEffect(() => { latestLayers.current = layers; }, [layers]);
  useEffect(() => { stateCb.current = onStateSelect; }, [onStateSelect]);
  useEffect(() => { coordCb.current = onCoords; }, [onCoords]);

  useEffect(() => {
    if (!el.current || map.current) return;

    const m = new Map({
      container: el.current,
      center: [78.9629, 20.5937],
      zoom: 4.25,
      minZoom: 3,
      maxZoom: 10,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap contributors",
          },
        },
        layers: [
          { id: "osm", type: "raster", source: "osm", paint: { "raster-opacity": 0.78 } },
        ],
      },
    });

    map.current = m;
    m.addControl(new NavigationControl({ showCompass: true }), "top-left");
    m.on("mousemove", e => coordCb.current?.(e.lngLat.lat, e.lngLat.lng));

    m.on("load", async () => {
      try {
        const current = latestLayers.current;
        const states = await fetch(INDIA, { cache: "no-store" }).then(r => {
          if (!r.ok) throw new Error("India boundary data unavailable");
          return r.json();
        });

        if (!m.getSource("india-states")) {
          m.addSource("india-states", { type: "geojson", data: states });
          m.addLayer({
            id: "states-fill",
            type: "fill",
            source: "india-states",
            layout: { visibility: current.terrain ? "visible" : "none" },
            paint: { "fill-color": "#102a39", "fill-opacity": 0.22 },
          });
          m.addLayer({
            id: "states-outline",
            type: "line",
            source: "india-states",
            layout: { visibility: current.terrain ? "visible" : "none" },
            paint: { "line-color": "#9fb4bd", "line-width": 1.1, "line-opacity": 0.8 },
          });

          m.on("click", "states-fill", e => {
            const p = e.features?.[0]?.properties as Record<string, unknown> | undefined;
            const name = String(p?.shapeName ?? p?.NAME_1 ?? p?.st_nm ?? p?.STATE ?? "India");
            stateCb.current?.(name);
            new Popup({ closeButton: true, closeOnClick: true })
              .setLngLat(e.lngLat)
              .setHTML(`<strong>${escapeHtml(name)}</strong><br/><small>State selected</small>`)
              .addTo(m);
          });
          m.on("mouseenter", "states-fill", () => { m.getCanvas().style.cursor = "pointer"; });
          m.on("mouseleave", "states-fill", () => { m.getCanvas().style.cursor = ""; });
        }

        const rainfall = await fetch(`/api/rainfall/grid/${DATE}`, { cache: "no-store" })
          .then(r => r.ok ? r.json() : null).catch(() => null);
        if (rainfall?.features && !m.getSource("rainfall")) {
          m.addSource("rainfall", { type: "geojson", data: rainfall });
          m.addLayer({
            id: "rainfall",
            type: "circle",
            source: "rainfall",
            layout: { visibility: current.satellite || current.anomalies ? "visible" : "none" },
            paint: {
              "circle-radius": 5,
              "circle-color": ["interpolate", ["linear"], ["get", "rainfall_mm"], 0, "#38bdf8", 50, "#ffc176", 100, "#ff5f5f"],
              "circle-opacity": 0.72,
              "circle-stroke-color": "#dff8ff",
              "circle-stroke-width": 0.5,
            },
          });
        }

        const events = await fetch(`/api/extreme-events/rainfall/geojson/${DATE}`, { cache: "no-store" })
          .then(r => r.ok ? r.json() : null).catch(() => null);
        if (events?.features && !m.getSource("events")) {
          m.addSource("events", { type: "geojson", data: events });
          m.addLayer({
            id: "events",
            type: "circle",
            source: "events",
            layout: { visibility: current.events ? "visible" : "none" },
            paint: { "circle-radius": 6, "circle-color": "#ffb4ab", "circle-stroke-color": "#ff5f5f", "circle-stroke-width": 1.2 },
          });
        }

        const risk = await fetch(`/api/risk/grid/${DATE}`, { cache: "no-store" })
          .then(r => r.ok ? r.json() : null).catch(() => null);
        if (risk?.features && !m.getSource("risk")) {
          m.addSource("risk", { type: "geojson", data: risk });
          m.addLayer({
            id: "risk",
            type: "circle",
            source: "risk",
            layout: { visibility: current.risk ? "visible" : "none" },
            paint: {
              "circle-radius": 5,
              "circle-color": ["match", ["get", "risk_category"], "Extreme", "#ef4444", "High", "#f97316", "Moderate", "#ffc176", "#38bdf8"],
              "circle-opacity": 0.78,
            },
          });
        }
      } catch (e) {
        console.error("Climate map data error", e);
      }
    });

    return () => {
      m.remove();
      map.current = null;
    };
  }, []);

  useEffect(() => {
    const m = map.current;
    if (!m || !m.isStyleLoaded()) return;
    const set = (id: string, visible: boolean) => {
      if (m.getLayer(id)) m.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
    };
    set("states-fill", layers.terrain);
    set("states-outline", layers.terrain);
    set("rainfall", layers.satellite || layers.anomalies);
    set("events", layers.events);
    set("risk", layers.risk);
  }, [layers]);

  useEffect(() => {
    const m = map.current;
    if (!m || !zoomRequest) return;
    if (zoomRequest.type === "in") m.zoomIn();
    if (zoomRequest.type === "out") m.zoomOut();
    if (zoomRequest.type === "reset") m.fitBounds([[68, 6], [97, 36]], { padding: 40, duration: 600 });
  }, [zoomRequest]);

  return <div ref={el} className="climate-map" aria-label="Interactive India climate map" />;
}

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
