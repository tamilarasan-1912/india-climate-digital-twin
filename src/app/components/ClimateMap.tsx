"use client";

import { useEffect, useRef, useState } from "react";
import {
  Map,
  NavigationControl,
  Popup,
  type GeoJSONSourceSpecification,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

type LayerKey =
  | "rainfall"
  | "temperature"
  | "lst"
  | "sst"
  | "anomalies"
  | "risk"
  | "events";

type LayerStatus = {
  status: string;
  data_available: boolean;
  provider?: string;
  message?: string;
};

type Props = {
  layers: Record<LayerKey, boolean>;
  date?: string;
  onStateSelect?: (name: string) => void;
  onCoords?: (lat: number, lon: number) => void;
  onLayerStatus?: (status: Partial<Record<LayerKey, LayerStatus>>) => void;
  selectedState?: string;
  districtMetrics?: Record<
    string,
    {
      valid_grid_cells?: number;
      mean_rainfall_mm?: number;
      maximum_rainfall_mm?: number;
      risk_category?: string;
    }
  >;
  zoomRequest?: { type: "in" | "out" | "reset"; nonce: number };
};

const INDIA = "/data/india/india-states.geojson";
const FIT: [[number, number], [number, number]] = [
  [68, 6],
  [97, 36],
];
const DATA_LAYERS: LayerKey[] = [
  "temperature",
  "lst",
  "sst",
  "anomalies",
  "risk",
  "events",
];
const EMPTY_FEATURE_COLLECTION = {
  type: "FeatureCollection" as const,
  features: [],
};

export default function ClimateMap({
  layers,
  date = "2024-07-15",
  onStateSelect,
  onCoords,
  onLayerStatus,
  selectedState = "INDIA",
  districtMetrics,
  zoomRequest,
}: Props) {
  const el = useRef<HTMLDivElement | null>(null);
  const map = useRef<Map | null>(null);
  const dateRef = useRef(date);
  const latestLayers = useRef(layers);
  const stateCb = useRef(onStateSelect);
  const coordCb = useRef(onCoords);
  const statusCb = useRef(onLayerStatus);
  const metricsRef = useRef(districtMetrics);
  const requestRef = useRef(0);
  const reloadDateRef = useRef<(requestedDate: string) => Promise<void>>(async () => undefined);
  const previousDateRef = useRef(date);
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);
  const [layerStatus, setLayerStatus] = useState<Partial<Record<LayerKey, LayerStatus>>>({});

  useEffect(() => {
    dateRef.current = date;
  }, [date]);
  useEffect(() => {
    latestLayers.current = layers;
  }, [layers]);
  useEffect(() => {
    stateCb.current = onStateSelect;
  }, [onStateSelect]);
  useEffect(() => {
    coordCb.current = onCoords;
  }, [onCoords]);
  useEffect(() => {
    statusCb.current = onLayerStatus;
  }, [onLayerStatus]);
  useEffect(() => {
    metricsRef.current = districtMetrics;
  }, [districtMetrics]);
  useEffect(() => {
    if (!el.current || map.current) return;

    let disposed = false;
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
          {
            id: "osm",
            type: "raster",
            source: "osm",
            paint: { "raster-opacity": 0.72 },
          },
        ],
      },
    });
    map.current = m;
    m.addControl(new NavigationControl({ showCompass: true }), "top-left");
    m.setPitch(35);
    m.on("mousemove", event =>
      coordCb.current?.(event.lngLat.lat, event.lngLat.lng),
    );
    m.on("error", event => {
      // Tile failures are reported in the status overlay, but do not tear down
      // the map: OSM/terrain and the local administrative layer can still be
      // useful when one provider is temporarily unavailable.
      const message = event.error instanceof Error ? event.error.message : "Map resource unavailable";
      if (!disposed && message) setMapError(current => current ?? message);
    });

    const publishStatus = (next: Partial<Record<LayerKey, LayerStatus>>) => {
      if (disposed) return;
      setLayerStatus(next);
      statusCb.current?.(next);
    };

    const updateGeoJSONLayer = (
      key: LayerKey,
      payload: Record<string, unknown> | null,
    ) => {
      const sourceId = `climate-${key}`;
      const layerId = sourceId;
      const hasFeatures = Array.isArray(payload?.features);
      const sourceData = hasFeatures ? payload : EMPTY_FEATURE_COLLECTION;
      const existing = m.getSource(sourceId);
      if (existing && "setData" in existing) {
        (existing as { setData: (data: unknown) => void }).setData(sourceData);
      } else if (!existing) {
        const source: GeoJSONSourceSpecification = {
          type: "geojson",
          data: sourceData as GeoJSON.FeatureCollection,
        };
        m.addSource(sourceId, source);
      }

      if (m.getLayer(layerId)) return;
      if (key === "events") {
        m.addLayer({
          id: layerId,
          type: "circle",
          source: sourceId,
          paint: {
            "circle-radius": 6,
            "circle-color": "#ff8b82",
            "circle-stroke-color": "#fff0ee",
            "circle-stroke-width": 1.2,
            "circle-opacity": 0.9,
          },
          layout: {
            visibility: latestLayers.current.events ? "visible" : "none",
          },
        });
      } else if (key === "risk") {
        m.addLayer({
          id: layerId,
          type: "circle",
          source: sourceId,
          paint: {
            "circle-radius": 5,
            "circle-color": [
              "match",
              ["get", "risk_category"],
              "extreme",
              "#ef4444",
              "high",
              "#f97316",
              "moderate",
              "#ffc176",
              "low",
              "#38bdf8",
              "#64748b",
            ],
            "circle-opacity": 0.78,
          },
          layout: {
            visibility: latestLayers.current.risk ? "visible" : "none",
          },
        });
      } else {
        m.addLayer({
          id: layerId,
          type: "circle",
          source: sourceId,
          paint: {
            "circle-radius": [
              "interpolate",
              ["linear"],
              ["zoom"],
              3,
              2.5,
              7,
              6,
            ],
            "circle-color": "#7ddfff",
            "circle-opacity": 0.7,
          },
          layout: {
            visibility: latestLayers.current[key] ? "visible" : "none",
          },
        });
      }
    };

    const loadClimateLayers = async (requestedDate: string) => {
      const requestId = ++requestRef.current;
      const [rainfallStatus, responses] = await Promise.all([
        fetch(`/api/climate/layers/rainfall?date=${requestedDate}`, { cache: "no-store" })
          .then(response => (response.ok ? response.json() : null))
          .catch(() => null),
        Promise.all(
          DATA_LAYERS.map(async key => {
            try {
              const response = await fetch(`/api/gods-eye/layer/${key}/${requestedDate}`, {
                cache: "no-store",
              });
              const payload = response.ok ? ((await response.json()) as Record<string, unknown>) : null;
              return [key, payload] as const;
            } catch {
              return [key, null] as const;
            }
          }),
        ),
      ]);

      if (disposed || requestId !== requestRef.current || dateRef.current !== requestedDate) return;
      const nextStatus: Partial<Record<LayerKey, LayerStatus>> = {};
      for (const [key, payload] of responses) {
        const hasFeatures = Array.isArray(payload?.features);
        nextStatus[key] = {
          status: String(payload?.status ?? (hasFeatures ? "AVAILABLE" : "NO_DATA")),
          data_available: Boolean(payload?.data_available ?? hasFeatures),
          provider: typeof payload?.provider === "string" ? payload.provider : undefined,
          message: typeof payload?.scientific_note === "string" ? payload.scientific_note : undefined,
        };
        updateGeoJSONLayer(key, payload);
      }
      nextStatus.rainfall = {
        status: String(rainfallStatus?.status ?? "NO_DATA"),
        data_available: Boolean(rainfallStatus?.data_available),
        provider: "IMD",
        message: typeof rainfallStatus?.scientific_note === "string" ? rainfallStatus.scientific_note : undefined,
      };
      publishStatus(nextStatus);
    };

    reloadDateRef.current = loadClimateLayers;

    const load = async () => {
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

        const statesResponse = await fetch(INDIA, { cache: "no-store" });
        if (!statesResponse.ok) throw new Error("India boundary data unavailable");
        const states = (await statesResponse.json()) as Record<string, unknown>;
        if (!Array.isArray(states.features) || states.features.length === 0) {
          throw new Error("India boundary data contains no features");
        }

        m.addSource("india-states", { type: "geojson", data: states as unknown as GeoJSON.FeatureCollection });
        m.addLayer({
          id: "states-fill",
          type: "fill",
          source: "india-states",
          paint: { "fill-color": "#123042", "fill-opacity": 0.2 },
        });
        m.addLayer({
          id: "states-outline",
          type: "line",
          source: "india-states",
          paint: {
            "line-color": "#b6c7cf",
            "line-width": 1.1,
            "line-opacity": 0.82,
          },
        });

        m.on("click", "states-fill", event => {
          const properties = event.features?.[0]?.properties as Record<string, unknown> | undefined;
          const name = String(
            properties?.shapeName ?? properties?.NAME_1 ?? properties?.st_nm ?? properties?.STATE ?? "India",
          );
          stateCb.current?.(name);
          new Popup({ closeButton: true, closeOnClick: true })
            .setLngLat(event.lngLat)
            .setHTML(
              `<strong>${escapeHtml(name)}</strong><br/><small>CLIMATE OBSERVATION · ${escapeHtml(dateRef.current)}</small>`,
            )
            .addTo(m);
        });
        m.on("mouseenter", "states-fill", () => {
          m.getCanvas().style.cursor = "pointer";
        });
        m.on("mouseleave", "states-fill", () => {
          m.getCanvas().style.cursor = "";
        });

        m.addSource("climate-rainfall", {
          type: "raster",
          tiles: [`/api/climate/tiles/rainfall/${dateRef.current}/{z}/{x}/{y}.png`],
          tileSize: 256,
          attribution: "IMD rainfall data",
        });
        m.addLayer({
          id: "climate-rainfall",
          type: "raster",
          source: "climate-rainfall",
          paint: { "raster-opacity": 0.68, "raster-fade-duration": 150 },
          layout: {
            visibility: latestLayers.current.rainfall ? "visible" : "none",
          },
        });

        await loadClimateLayers(dateRef.current);
        m.on("click", DATA_LAYERS.map(key => `climate-${key}`), event => {
          const properties = event.features?.[0]?.properties as Record<string, unknown> | undefined;
          if (!properties) return;
          const rows = Object.entries(properties)
            .filter(([, value]) => value !== null && value !== "")
            .slice(0, 8)
            .map(([key, value]) => `<div><b>${escapeHtml(key)}</b>: ${escapeHtml(String(value))}</div>`)
            .join("");
          new Popup({ closeButton: true })
            .setLngLat(event.lngLat)
            .setHTML(`${rows || "CLIMATE OBSERVATION"}<small>DATE · ${escapeHtml(dateRef.current)}</small>`)
            .addTo(m);
        });
        if (!disposed) {
          setMapReady(true);
          setMapError(null);
        }
      } catch (error) {
        if (!disposed) {
          setMapError(error instanceof Error ? error.message : "Failed to initialize climate map");
        }
      }
    };

    m.once("load", () => {
      void load();
    });

    return () => {
      disposed = true;
      requestRef.current += 1;
      reloadDateRef.current = async () => undefined;
      m.remove();
      map.current = null;
    };
  }, []);

  // A date change updates the existing raster source and GeoJSON sources. The
  // map instance stays alive, so changing the timeline no longer resets zoom,
  // pitch, popups, or the selected state.
  useEffect(() => {
    const m = map.current;
    if (!m || !mapReady || previousDateRef.current === date) return;
    previousDateRef.current = date;
    const source = m.getSource("climate-rainfall") as {
      setTiles?: (tiles: string[]) => void;
    } | undefined;
    source?.setTiles?.([`/api/climate/tiles/rainfall/${date}/{z}/{x}/{y}.png`]);
    m.triggerRepaint();
    void reloadDateRef.current(date);
  }, [date, mapReady]);

  useEffect(() => {
    const m = map.current;
    if (!m || !m.isStyleLoaded()) return;
    (Object.keys(layers) as LayerKey[]).forEach(key => {
      const id = key === "rainfall" ? "climate-rainfall" : `climate-${key}`;
      if (m.getLayer(id)) {
        m.setLayoutProperty(id, "visibility", layers[key] ? "visible" : "none");
      }
    });
  }, [layers]);

  useEffect(() => {
    const m = map.current;
    if (!m || !m.isStyleLoaded() || !selectedState || selectedState.toUpperCase() === "INDIA") {
      if (m?.getLayer("india-district-fill")) m.setLayoutProperty("india-district-fill", "visibility", "none");
      if (m?.getLayer("india-district-outline")) m.setLayoutProperty("india-district-outline", "visibility", "none");
      return;
    }
    let alive = true;
    fetch(`/api/india/districts/geojson?state=${encodeURIComponent(selectedState)}`, {
      cache: "no-store",
    })
      .then(response => (response.ok ? response.json() : null))
      .then(data => {
        if (!alive || !data?.features?.length) return;
        const sourceId = "india-districts";
        const existing = m.getSource(sourceId);
        if (existing && "setData" in existing) {
          (existing as { setData: (value: unknown) => void }).setData(data);
        } else {
          m.addSource(sourceId, { type: "geojson", data });
          m.addLayer({
            id: "india-district-fill",
            type: "fill",
            source: sourceId,
            paint: { "fill-color": "#0e5c72", "fill-opacity": 0.12 },
          });
          m.addLayer({
            id: "india-district-outline",
            type: "line",
            source: sourceId,
            paint: { "line-color": "#65d7ef", "line-width": 0.65, "line-opacity": 0.65 },
          });
          m.on("click", "india-district-fill", event => {
            const properties = event.features?.[0]?.properties as Record<string, unknown> | undefined;
            const name = String(properties?.shapeName ?? properties?.NAME_2 ?? "District");
            const id = String(properties?.shapeID ?? "");
            const metric = metricsRef.current?.[id];
            const html = metric?.valid_grid_cells
              ? `<strong>${escapeHtml(name)}</strong><br/><small>OBSERVED · ${metric.valid_grid_cells} IMD GRID CELLS</small><br/>Mean ${escapeHtml(String(metric.mean_rainfall_mm))} mm · Max ${escapeHtml(String(metric.maximum_rainfall_mm))} mm<br/><small>Risk ${escapeHtml(String(metric.risk_category))}</small>`
              : `<strong>${escapeHtml(name)}</strong><br/><small>DISTRICT GEOMETRY AVAILABLE</small><br/><small>NO IMD GRID-POINT CENTRE IN POLYGON · NO ESTIMATE</small>`;
            new Popup({ closeButton: true }).setLngLat(event.lngLat).setHTML(html).addTo(m);
          });
        }
        if (m.getLayer("india-district-fill")) m.setLayoutProperty("india-district-fill", "visibility", "visible");
        if (m.getLayer("india-district-outline")) m.setLayoutProperty("india-district-outline", "visibility", "visible");
        const bounds = featureBounds(data.features);
        if (bounds) m.fitBounds(bounds, { padding: 70, maxZoom: 7.2, duration: 700 });
      })
      .catch(error => {
        if (alive) setMapError(error instanceof Error ? error.message : "District boundary unavailable");
      });
    return () => {
      alive = false;
    };
  }, [selectedState, mapReady]);

  useEffect(() => {
    const m = map.current;
    if (!m || !zoomRequest) return;
    if (zoomRequest.type === "in") m.zoomIn({ duration: 250 });
    if (zoomRequest.type === "out") m.zoomOut({ duration: 250 });
    if (zoomRequest.type === "reset") m.fitBounds(FIT, { padding: 40, duration: 600 });
  }, [zoomRequest]);

  const unavailable = Object.values(layerStatus).filter(item => item && !item.data_available).length;
  return (
    <div className="climate-map-shell">
      <div ref={el} className="climate-map" aria-label="India Climate Digital Twin God's-Eye map" />
      {mapError && (
        <div className="climate-map-error" role="status">
          <strong>MAP DATA STATUS</strong>
          <span>{mapError}</span>
        </div>
      )}
      {mapReady && unavailable > 0 && (
        <div className="climate-map-status" role="status">
          {unavailable} layer{unavailable === 1 ? "" : "s"} report NO DATA or require a provider.
        </div>
      )}
    </div>
  );
}

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function featureBounds(features: any[]): [[number, number], [number, number]] | null {
  let minLon = Infinity;
  let minLat = Infinity;
  let maxLon = -Infinity;
  let maxLat = -Infinity;
  const visit = (coordinates: any): void => {
    if (!Array.isArray(coordinates)) return;
    if (typeof coordinates[0] === "number" && typeof coordinates[1] === "number") {
      minLon = Math.min(minLon, coordinates[0]);
      maxLon = Math.max(maxLon, coordinates[0]);
      minLat = Math.min(minLat, coordinates[1]);
      maxLat = Math.max(maxLat, coordinates[1]);
      return;
    }
    coordinates.forEach(visit);
  };
  features.forEach(feature => visit(feature?.geometry?.coordinates));
  return Number.isFinite(minLon) && Number.isFinite(minLat)
    ? [[minLon, minLat], [maxLon, maxLat]]
    : null;
}
