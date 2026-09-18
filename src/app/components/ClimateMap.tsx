"use client";

import { useEffect, useRef } from "react";
import { Map, NavigationControl, Popup, type GeoJSONSourceSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

type LayerKey = "rainfall" | "temperature" | "lst" | "sst" | "anomalies" | "risk" | "events";
type Props = {
  layers: Record<LayerKey, boolean>;
  date?: string;
  onStateSelect?: (name: string) => void;
  onCoords?: (lat: number, lon: number) => void;
  zoomRequest?: { type: "in" | "out" | "reset"; nonce: number };
};

const INDIA = "/data/india/india-states.geojson";
const FIT: [[number, number], [number, number]] = [[68, 6], [97, 36]];

export default function ClimateMap({ layers, date = "2024-07-15", onStateSelect, onCoords, zoomRequest }: Props) {
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
        layers: [{ id: "osm", type: "raster", source: "osm", paint: { "raster-opacity": 0.72 } }],
      },
    });
    map.current = m;
    m.addControl(new NavigationControl({ showCompass: true }), "top-left");
    m.setPitch(35);
    m.on("mousemove", e => coordCb.current?.(e.lngLat.lat, e.lngLat.lng));

    m.on("load", async () => {
      try {
        if (!m.getSource("india-terrain")) {
          m.addSource("india-terrain", {
            type: "raster-dem",
            tiles: ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"],
            tileSize: 256,
            encoding: "terrarium",
            maxzoom: 14,
          });
          m.setTerrain({ source: "india-terrain", exaggeration: 1.0 });
        }

        const states = await fetch(INDIA, { cache: "no-store" }).then(r => {
          if (!r.ok) throw new Error("India boundary data unavailable");
          return r.json();
        });
        m.addSource("india-states", { type: "geojson", data: states });
        m.addLayer({
          id: "states-fill", type: "fill", source: "india-states",
          paint: { "fill-color": "#123042", "fill-opacity": 0.20 },
        });
        m.addLayer({
          id: "states-outline", type: "line", source: "india-states",
          paint: { "line-color": "#b6c7cf", "line-width": 1.1, "line-opacity": 0.82 },
        });
        m.addLayer({
          id: "state-hover", type: "line", source: "india-states",
          filter: ["==", ["id"], ""],
          paint: { "line-color": "#7ddfff", "line-width": 2.5, "line-opacity": 0 },
        });

        m.on("click", "states-fill", e => {
          const p = e.features?.[0]?.properties as Record<string, unknown> | undefined;
          const name = String(p?.shapeName ?? p?.NAME_1 ?? p?.st_nm ?? p?.STATE ?? "India");
          stateCb.current?.(name);
          new Popup({ closeButton: true, closeOnClick: true })
            .setLngLat(e.lngLat)
            .setHTML(`<strong>${escapeHtml(name)}</strong><br/><small>CLIMATE OBSERVATION · ${escapeHtml(date)}</small>`)
            .addTo(m);
        });
        m.on("mouseenter", "states-fill", () => { m.getCanvas().style.cursor = "pointer"; });
        m.on("mouseleave", "states-fill", () => { m.getCanvas().style.cursor = ""; });

        const keys: LayerKey[] = ["rainfall", "temperature", "lst", "sst", "anomalies", "risk", "events"];
        const payloads = await Promise.all(keys.map(async key => {
          try {
            const r = await fetch(`/api/gods-eye/layer/${key}/${date}`, { cache: "no-store" });
            return [key, r.ok ? await r.json() : null] as const;
          } catch { return [key, null] as const; }
        }));

        for (const [key, payload] of payloads) {
          if (!payload?.features || !Array.isArray(payload.features)) continue;
          const sourceId = `climate-${key}`;
          const layerId = `climate-${key}`;
          const source: GeoJSONSourceSpecification = { type: "geojson", data: payload };
          m.addSource(sourceId, source);
          if (key === "events") {
            m.addLayer({
              id: layerId, type: "circle", source: sourceId,
              paint: { "circle-radius": 6, "circle-color": "#ff8b82", "circle-stroke-color": "#fff0ee", "circle-stroke-width": 1.2, "circle-opacity": 0.9 },
              layout: { visibility: latestLayers.current.events ? "visible" : "none" },
            });
          } else if (key === "risk") {
            m.addLayer({
              id: layerId, type: "circle", source: sourceId,
              paint: {
                "circle-radius": 5,
                "circle-color": ["match", ["get", "risk_category"], "extreme", "#ef4444", "high", "#f97316", "moderate", "#ffc176", "low", "#38bdf8", "#64748b"],
                "circle-opacity": 0.78,
              },
              layout: { visibility: latestLayers.current.risk ? "visible" : "none" },
            });
          } else {
            m.addLayer({
              id: layerId, type: "circle", source: sourceId,
              paint: {
                "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 2.5, 7, 6],
                "circle-color": key === "rainfall"
                  ? ["interpolate", ["linear"], ["get", "rainfall_mm"], 0, "#38bdf8", 50, "#ffc176", 100, "#ff5f5f"]
                  : "#7ddfff",
                "circle-opacity": 0.70,
              },
              layout: { visibility: latestLayers.current[key] ? "visible" : "none" },
            });
          }
        }

        m.on("click", ["climate-rainfall", "climate-risk", "climate-events"], e => {
          const p = e.features?.[0]?.properties as Record<string, unknown> | undefined;
          if (!p) return;
          const rows = Object.entries(p).filter(([, v]) => v !== null && v !== "").slice(0, 8)
            .map(([k, v]) => `<div><b>${escapeHtml(k)}</b>: ${escapeHtml(String(v))}</div>`).join("");
          new Popup({ closeButton: true }).setLngLat(e.lngLat).setHTML(rows || "CLIMATE OBSERVATION").addTo(m);
        });
      } catch (error) {
        console.error("Climate God's-Eye map data error", error);
      }
    });

    return () => { m.remove(); map.current = null; };
  }, [date]);

  useEffect(() => {
    const m = map.current;
    if (!m || !m.isStyleLoaded()) return;
    const set = (key: LayerKey, visible: boolean) => {
      const id = `climate-${key}`;
      if (m.getLayer(id)) m.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
    };
    (Object.keys(layers) as LayerKey[]).forEach(key => set(key, layers[key]));
    if (m.getLayer("states-fill")) m.setPaintProperty("states-fill", "fill-opacity", 0.20);
    if (m.getLayer("states-outline")) m.setPaintProperty("states-outline", "line-opacity", 0.82);
  }, [layers]);

  useEffect(() => {
    const m = map.current;
    if (!m || !zoomRequest) return;
    if (zoomRequest.type === "in") m.zoomIn({ duration: 250 });
    if (zoomRequest.type === "out") m.zoomOut({ duration: 250 });
    if (zoomRequest.type === "reset") m.fitBounds(FIT, { padding: 40, duration: 600 });
  }, [zoomRequest]);

  return <div ref={el} className="climate-map" aria-label="India Climate Digital Twin God's-Eye map" />;
}

function escapeHtml(value: string) {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}
