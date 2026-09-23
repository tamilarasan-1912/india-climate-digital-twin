"use client";

import { useEffect, useRef, useState } from "react";
import { Map, NavigationControl, Popup, type LayerSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

export type MapLayerKey = "rainfall" | "temperature" | "lst" | "sst" | "anomalies" | "risk" | "events";
type Props = {
  layers: Record<MapLayerKey, boolean>;
  date?: string;
  onStateSelect?: (name: string) => void;
  onCoords?: (lat: number, lon: number) => void;
  selectedState?: string;
  districtMetrics?: Record<string, { valid_grid_cells?: number; mean_rainfall_mm?: number; maximum_rainfall_mm?: number; risk_category?: string }>;
  zoomRequest?: { type: "in" | "out" | "reset"; nonce: number };
};

const INDIA = "/data/india/india-states.geojson";
const FIT: [[number, number], [number, number]] = [[68, 6], [97, 36]];
// Every layer key that is drawn as point geometry from /api/gods-eye/layer.
const POINT_LAYERS: MapLayerKey[] = ["temperature", "lst", "sst", "anomalies", "risk", "events"];

export default function ClimateMap({ layers, date = "2024-07-15", onStateSelect, onCoords, zoomRequest, selectedState = "INDIA", districtMetrics }: Props) {
  const el = useRef<HTMLDivElement | null>(null);
  const map = useRef<Map | null>(null);
  const latestLayers = useRef(layers);
  const stateCb = useRef(onStateSelect);
  const coordCb = useRef(onCoords);
  // The popup handler is bound once when the layer is created, so it reads the
  // latest metrics from a ref rather than capturing props at bind time.
  const metricsRef = useRef(districtMetrics);
  const latestDate = useRef(date);
  // Bumped once the style has loaded. Data effects gate on it because sources
  // cannot be added before the style exists.
  const [styleReady, setStyleReady] = useState(0);

  useEffect(() => { latestLayers.current = layers; }, [layers]);
  useEffect(() => { stateCb.current = onStateSelect; }, [onStateSelect]);
  useEffect(() => { coordCb.current = onCoords; }, [onCoords]);
  useEffect(() => { metricsRef.current = districtMetrics; }, [districtMetrics]);
  useEffect(() => { latestDate.current = date; }, [date]);

  // The map is created exactly once. It used to depend on `date`, so every date
  // change tore down the WebGL context, the DEM terrain source and every layer,
  // then rebuilt them — which made timeline scrubbing unusable. Temporal updates
  // now mutate existing sources instead.
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

        m.on("click", "states-fill", e => {
          const p = e.features?.[0]?.properties as Record<string, unknown> | undefined;
          const name = String(p?.shapeName ?? p?.NAME_1 ?? p?.st_nm ?? p?.STATE ?? "India");
          stateCb.current?.(name);
          new Popup({ closeButton: true, closeOnClick: true })
            .setLngLat(e.lngLat)
            .setHTML(`<strong>${escapeHtml(name)}</strong><br/><small>CLIMATE OBSERVATION · ${escapeHtml(latestDate.current)}</small>`)
            .addTo(m);
        });
        m.on("mouseenter", "states-fill", () => { m.getCanvas().style.cursor = "pointer"; });
        m.on("mouseleave", "states-fill", () => { m.getCanvas().style.cursor = ""; });

        // Rainfall is served as a provider-backed raster tile layer so the
        // browser does not download the entire IMD point grid for every date.
        // The tile URL embeds the date, so a temporal update replaces the source
        // rather than the map.
        m.addSource("climate-rainfall", {
          type: "raster",
          tiles: [rainfallTileUrl(latestDate.current)],
          tileSize: 256,
          attribution: "IMD rainfall data",
        });
        m.addLayer({
          id: "climate-rainfall",
          type: "raster",
          source: "climate-rainfall",
          paint: { "raster-opacity": 0.68, "raster-fade-duration": 150 },
          layout: { visibility: latestLayers.current.rainfall ? "visible" : "none" },
        });

        // No scenario overlay is drawn on the map. The scenario engine returns
        // national aggregate hazard statistics with no spatial geometry, so a
        // map layer would have nothing truthful to render.
        for (const key of POINT_LAYERS) {
          const sourceId = `climate-${key}`;
          m.addSource(sourceId, { type: "geojson", data: emptyCollection() });
          m.addLayer(pointLayerSpec(key, sourceId));
        }

        m.on("click", ["climate-rainfall", "climate-risk", "climate-events"], e => {
          const p = e.features?.[0]?.properties as Record<string, unknown> | undefined;
          if (!p) return;
          const rows = Object.entries(p).filter(([, v]) => v !== null && v !== "").slice(0, 8)
            .map(([k, v]) => `<div><b>${escapeHtml(k)}</b>: ${escapeHtml(String(v))}</div>`).join("");
          new Popup({ closeButton: true }).setLngLat(e.lngLat).setHTML(rows || "CLIMATE OBSERVATION").addTo(m);
        });

        // The style is only usable once loaded; signal so the data effects below
        // can populate the point layers and district geometry.
        setStyleReady(v => v + 1);
      } catch (error) {
        console.error("Climate God's-Eye map data error", error);
      }
    });

    return () => { m.remove(); map.current = null; };
  }, []);

  // Layer visibility only. Runs after the style is ready.
  useEffect(() => {
    const m = map.current;
    if (!m || !m.isStyleLoaded()) return;
    for (const key of ALL_LAYERS) {
      const id = `climate-${key}`;
      if (m.getLayer(id)) m.setLayoutProperty(id, "visibility", layers[key] ? "visible" : "none");
    }
  }, [layers, styleReady]);

  // Temporal update: rainfall raster tiles and every point layer are re-pointed
  // at the new date. No map, source or layer is destroyed.
  useEffect(() => {
    const m = map.current;
    if (!m || !styleReady) return;
    // A layer must be removed before the source it references.
    if (m.getLayer("climate-rainfall")) m.removeLayer("climate-rainfall");
    if (m.getSource("climate-rainfall")) m.removeSource("climate-rainfall");
    m.addSource("climate-rainfall", {
      type: "raster",
      tiles: [rainfallTileUrl(date)],
      tileSize: 256,
      attribution: "IMD rainfall data",
    });
    m.addLayer({
      id: "climate-rainfall",
      type: "raster",
      source: "climate-rainfall",
      paint: { "raster-opacity": 0.68, "raster-fade-duration": 150 },
      layout: { visibility: latestLayers.current.rainfall ? "visible" : "none" },
    });

    let alive = true;
    const controller = new AbortController();
    (async () => {
      const payloads = await Promise.all(POINT_LAYERS.map(async key => {
        try {
          const r = await fetch(`/api/gods-eye/layer/${key}/${date}`, { cache: "no-store", signal: controller.signal });
          return [key, r.ok ? await r.json() : null] as const;
        } catch { return [key, null] as const; }
      }));
      if (!alive) return;
      for (const [key, payload] of payloads) {
        const source = m.getSource(`climate-${key}`);
        if (!source || !("setData" in source)) continue;
        // A layer with no validated provider returns no features; the source is
        // emptied rather than left showing the previous date's points.
        const data = payload?.features?.length ? payload : emptyCollection();
        (source as unknown as { setData(d: GeoJSON.FeatureCollection): void }).setData(data);
      }
    })();
    return () => { alive = false; controller.abort(); };
  }, [date, styleReady]);

  // Scenario overlay is intentionally absent: see the note where layers are added.

  useEffect(() => {
    const m = map.current;
    if (!m || !m.isStyleLoaded() || !selectedState || selectedState.toUpperCase() === "INDIA") {
      if (m?.getLayer("india-district-fill")) m.setLayoutProperty("india-district-fill", "visibility", "none");
      if (m?.getLayer("india-district-outline")) m.setLayoutProperty("india-district-outline", "visibility", "none");
      return;
    }
    let alive = true;
    fetch(`/api/india/districts/geojson?state=${encodeURIComponent(selectedState)}`, { cache: "no-store" })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (!alive || !data?.features?.length) return;
        const sourceId = "india-districts";
        const source = m.getSource(sourceId);
        if (source && "setData" in source) (source as any).setData(data);
        else {
          m.addSource(sourceId, { type: "geojson", data });
          m.addLayer({ id: "india-district-fill", type: "fill", source: sourceId, paint: { "fill-color": "#0e5c72", "fill-opacity": 0.12 }, layout: { visibility: "visible" } });
          m.addLayer({ id: "india-district-outline", type: "line", source: sourceId, paint: { "line-color": "#65d7ef", "line-width": 0.65, "line-opacity": 0.65 }, layout: { visibility: "visible" } });
          m.on("click", "india-district-fill", e => {
            const p = e.features?.[0]?.properties as Record<string, unknown> | undefined;
            const name = String(p?.shapeName ?? p?.NAME_2 ?? "District");
            const id = String(p?.shapeID ?? "");
            const metric = metricsRef.current?.[id];
            const html = metric?.valid_grid_cells
              ? `<strong>${escapeHtml(name)}</strong><br/><small>OBSERVED · ${metric.valid_grid_cells} IMD GRID CELLS</small><br/>Mean ${escapeHtml(String(metric.mean_rainfall_mm))} mm · Max ${escapeHtml(String(metric.maximum_rainfall_mm))} mm<br/><small>Risk ${escapeHtml(String(metric.risk_category))}</small>`
              : `<strong>${escapeHtml(name)}</strong><br/><small>DISTRICT GEOMETRY AVAILABLE</small><br/><small>NO IMD GRID-POINT CENTRE IN POLYGON · NO ESTIMATE</small>`;
            new Popup({ closeButton: true }).setLngLat(e.lngLat).setHTML(html).addTo(m);
          });
        }
        if (m.getLayer("india-district-fill")) m.setLayoutProperty("india-district-fill", "visibility", "visible");
        if (m.getLayer("india-district-outline")) m.setLayoutProperty("india-district-outline", "visibility", "visible");
        const bbox = featureBounds(data.features);
        if (bbox) m.fitBounds(bbox, { padding: 70, maxZoom: 7.2, duration: 700 });
      })
      .catch(() => {});
    return () => { alive = false; };
  }, [selectedState, styleReady]);

  useEffect(() => {
    const m = map.current;
    if (!m || !zoomRequest) return;
    if (zoomRequest.type === "in") m.zoomIn({ duration: 250 });
    if (zoomRequest.type === "out") m.zoomOut({ duration: 250 });
    if (zoomRequest.type === "reset") m.fitBounds(FIT, { padding: 40, duration: 600 });
  }, [zoomRequest]);

  return <div ref={el} className="climate-map" aria-label="India Climate Digital Twin God's-Eye map" />;
}

const ALL_LAYERS: MapLayerKey[] = ["rainfall", ...POINT_LAYERS];

function rainfallTileUrl(date: string) {
  return `/api/climate/tiles/rainfall/${encodeURIComponent(date)}/{z}/{x}/{y}.png`;
}

function emptyCollection(): GeoJSON.FeatureCollection {
  return { type: "FeatureCollection", features: [] };
}

function pointLayerSpec(key: MapLayerKey, sourceId: string): LayerSpecification {
  const visibility = "none" as const;
  if (key === "events") {
    return {
      id: `climate-${key}`, type: "circle", source: sourceId,
      paint: { "circle-radius": 6, "circle-color": "#ff8b82", "circle-stroke-color": "#fff0ee", "circle-stroke-width": 1.2, "circle-opacity": 0.9 },
      layout: { visibility },
    };
  }
  if (key === "risk") {
    return {
      id: `climate-${key}`, type: "circle", source: sourceId,
      paint: {
        "circle-radius": 5,
        "circle-color": ["match", ["get", "risk_category"], "extreme", "#ef4444", "high", "#f97316", "moderate", "#ffc176", "low", "#38bdf8", "#64748b"],
        "circle-opacity": 0.78,
      },
      layout: { visibility },
    };
  }
  return {
    id: `climate-${key}`, type: "circle", source: sourceId,
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 2.5, 7, 6],
      "circle-color": "#7ddfff",
      "circle-opacity": 0.70,
    },
    layout: { visibility },
  };
}

function escapeHtml(value: string) {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

function featureBounds(features: any[]): [[number, number], [number, number]] | null {
  let minLon = Infinity, minLat = Infinity, maxLon = -Infinity, maxLat = -Infinity;
  const visit = (coords: any): void => {
    if (!Array.isArray(coords)) return;
    if (typeof coords[0] === "number" && typeof coords[1] === "number") {
      minLon = Math.min(minLon, coords[0]); maxLon = Math.max(maxLon, coords[0]);
      minLat = Math.min(minLat, coords[1]); maxLat = Math.max(maxLat, coords[1]); return;
    }
    for (const child of coords) visit(child);
  };
  for (const feature of features) visit(feature?.geometry?.coordinates);
  return Number.isFinite(minLon) ? [[minLon, minLat], [maxLon, maxLat]] : null;
}
