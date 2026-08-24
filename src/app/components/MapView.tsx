"use client";

import { useEffect, useRef, useState } from "react";

import {
  Map,
  NavigationControl,
  Popup,
} from "maplibre-gl";

import "maplibre-gl/dist/maplibre-gl.css";

import * as turf from "@turf/turf";

import type {
  Feature,
  FeatureCollection,
  GeoJsonProperties,
  MultiPolygon,
  Polygon,
} from "geojson";

/* ============================================================
   TYPES
   ============================================================ */

interface MapViewProps {
  onStateSelect?: (stateName: string) => void;
}

interface RainfallProperties {
  rainfall_mm?: number;
  date?: string;
}

interface ExtremeEventProperties {
  rainfall_mm?: number;
  category?: string;
  severity?: number;
  date?: string;
}

type ExtremeEventGeoJSON =
  FeatureCollection<
    GeoJSON.Point,
    ExtremeEventProperties
  >;

interface RiskProperties {
  rainfall_mm?: number;
  hazard_score?: number;
  risk_category?: string;
  rainfall_category?: string;
  date?: string;
}

type RiskGeoJSON =
  FeatureCollection<
    GeoJSON.Point,
    RiskProperties
  >;

type RainfallGeoJSON =
  FeatureCollection<
    GeoJSON.Point,
    RainfallProperties
  >;

interface StateProperties {
  __stateName?: string;
}

/* ============================================================
   CONSTANTS
   ============================================================ */

const STATE_SOURCE = "india-states";

const STATE_FILL_LAYER =
  "india-states-fill";

const STATE_OUTLINE_LAYER =
  "india-states-outline";

const SELECTED_STATE_FILL_LAYER =
  "selected-state-fill";

const SELECTED_STATE_OUTLINE_LAYER =
  "selected-state-outline";

const RAINFALL_SOURCE =
  "imd-rainfall";

const RAINFALL_HEATMAP_LAYER =
  "imd-rainfall-heatmap";

const RAINFALL_CIRCLE_LAYER =
  "imd-rainfall-circles";

const INDIA_GEOJSON_URL =
  "/data/india/india-states.geojson";

const RAINFALL_DATE =
  "2024-07-15";

const EXTREME_EVENT_SOURCE =
  "imd-extreme-events";

const EXTREME_EVENT_LAYER =
  "imd-extreme-events-circles";

const EXTREME_EVENT_LABEL_LAYER =
  "imd-extreme-events-labels";

const EXTREME_EVENT_API =
  `/api/extreme-events/rainfall/geojson/${RAINFALL_DATE}`;

const RISK_SOURCE =
  "climate-risk";

const RISK_LAYER =
  "climate-risk-circles";

const RISK_API =
  `/api/risk/grid/${RAINFALL_DATE}`;

/* ============================================================
   HELPERS
   ============================================================ */

function getStateName(
  properties: GeoJsonProperties
): string {
  if (!properties) {
    return "Unknown State";
  }

  const candidates = [
    properties.shapeName,
    properties.shapeName_en,
    properties.NAME_1,
    properties.NAME_1_EN,
    properties.name,
    properties.NAME,
    properties.st_nm,
    properties.ST_NM,
    properties.state,
    properties.State,
    properties.STATE,
  ];

  const value = candidates.find(
    (candidate) =>
      typeof candidate === "string" &&
      candidate.trim().length > 0
  );

  return value
    ? String(value).trim()
    : "Unknown State";
}

/* ============================================================
   COMPONENT
   ============================================================ */

export default function MapView({
  onStateSelect,
}: MapViewProps) {
  /* ==========================================================
     REFS
     ========================================================== */

  const containerRef =
    useRef<HTMLDivElement | null>(null);

  const mapRef =
    useRef<Map | null>(null);

  const statesRef =
    useRef<
      FeatureCollection<
        Polygon | MultiPolygon,
        StateProperties
      > | null
    >(null);

  const selectedStateIdRef =
    useRef<number | string | null>(null);

  const onStateSelectRef =
    useRef(onStateSelect);

  /* ==========================================================
     REACT STATE
     ========================================================== */

  const [mapReady, setMapReady] =
    useState(false);

  const [rainfallLoaded, setRainfallLoaded] =
    useState(false);

  const [rainfallError, setRainfallError] =
    useState<string | null>(null);

  const [extremeEventsLoaded, setExtremeEventsLoaded] =
    useState(false);

  const [extremeEventsError, setExtremeEventsError] =
    useState<string | null>(null);

  const [riskLoaded, setRiskLoaded] =
    useState(false);

  const [riskError, setRiskError] =
    useState<string | null>(null);

  const [mapError, setMapError] =
    useState<string | null>(null);

  /* ==========================================================
     CALLBACK REF
     ========================================================== */

  useEffect(() => {
    onStateSelectRef.current =
      onStateSelect;
  }, [onStateSelect]);

  /* ==========================================================
     MAP INITIALIZATION
     ========================================================== */

  useEffect(() => {
    if (!containerRef.current) {
      return;
    }

    if (mapRef.current) {
      return;
    }

    let cancelled = false;

    console.log(
      "Initializing MapLibre..."
    );

    /* ========================================================
       CREATE MAP
       ======================================================== */

    const map = new Map({
      container: containerRef.current,

      style: {
        version: 8,
        sources: {},
        layers: [],
      },

      center: [
        78.9629,
        20.5937,
      ],

      zoom: 4,

      minZoom: 2,

      maxZoom: 12,

    });

    mapRef.current = map;

    /* ========================================================
       NAVIGATION
       ======================================================== */

    map.addControl(
      new NavigationControl({
        visualizePitch: true,
      }),
      "top-right"
    );

    /* ========================================================
       MAP ERROR
       ======================================================== */

    map.on("error", (event) => {
      console.error(
        "MapLibre error:",
        event?.error ?? event
      );
    });

    /* ========================================================
       LOAD
       ======================================================== */

    map.once("load", async () => {
      if (cancelled) {
        return;
      }

      console.log(
        "MapLibre India map loaded."
      );

      try {
        /* ====================================================
           BASE MAP
           ==================================================== */

        map.addSource(
          "osm-basemap",
          {
            type: "raster",

            tiles: [
              "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            ],

            tileSize: 256,

            attribution:
              "© OpenStreetMap contributors",
          }
        );

        map.addLayer({
          id: "osm-layer",

          type: "raster",

          source: "osm-basemap",

          minzoom: 0,

          maxzoom: 19,
        });

        /* ====================================================
           LOAD DATA IN PARALLEL
           ==================================================== */

        const stateRequest =
          fetch(
            INDIA_GEOJSON_URL,
            {
              cache: "no-store",
            }
          );

        const rainfallRequest =
          fetch(
            `/api/rainfall/grid/${RAINFALL_DATE}`,
            {
              cache: "no-store",
            }
          );

        const extremeEventRequest =
          fetch(
            EXTREME_EVENT_API,
            {
              cache: "no-store",
            }
          );

        /* ====================================================
           STATE GEOJSON
           ==================================================== */

        let stateGeoJSON:
          FeatureCollection<
            Polygon | MultiPolygon,
            StateProperties
          > | null = null;

        try {
          const response =
            await stateRequest;

          if (!response.ok) {
            throw new Error(
              `India GeoJSON request failed with HTTP ${response.status}`
            );
          }

          const raw =
            (await response.json()) as FeatureCollection;

          if (
            raw.type !==
            "FeatureCollection"
          ) {
            throw new Error(
              "India GeoJSON is not a FeatureCollection."
            );
          }

          /*
           * Create a clean GeoJSON representation.
           *
           * Important:
           * We give every state a stable feature ID.
           *
           * This allows MapLibre feature-state to
           * highlight the state without depending
           * on a specific property name.
           */

          const processedFeatures =
            raw.features
              .filter(
                (feature) =>
                  feature.geometry &&
                  (
                    feature.geometry.type ===
                      "Polygon" ||
                    feature.geometry.type ===
                      "MultiPolygon"
                  )
              )
              .map(
                (feature, index) => ({
                  type: "Feature" as const,

                  id: index,

                  geometry:
                    feature.geometry as
                      | Polygon
                      | MultiPolygon,

                  properties: {
                    __stateName:
                      getStateName(
                        feature.properties
                      ),
                  },
                })
              );

          stateGeoJSON = {
            type: "FeatureCollection",

            features:
              processedFeatures,
          };

          statesRef.current =
            stateGeoJSON;

          console.log(
            "India GeoJSON loaded successfully."
          );

          console.log(
            "Number of state features:",
            processedFeatures.length
          );
        } catch (error) {
          console.error(
            "India GeoJSON loading error:",
            error
          );

          throw error;
        }

        /* ====================================================
           ADD STATE SOURCE
           ==================================================== */

        map.addSource(
          STATE_SOURCE,
          {
            type: "geojson",

            data: stateGeoJSON,
          }
        );

        /* ====================================================
           STATE BASE FILL
           ==================================================== */

        map.addLayer({
          id: STATE_FILL_LAYER,

          type: "fill",

          source: STATE_SOURCE,

          paint: {
            "fill-color":
              "#0ea5e9",

            "fill-opacity":
              0.025,
          },
        });

        /* ====================================================
           RAINFALL
           ==================================================== */

        let rainfallGeoJSON:
          RainfallGeoJSON = {
            type: "FeatureCollection",

            features: [],
          };

        try {
          const response =
            await rainfallRequest;

          if (!response.ok) {
            throw new Error(
              `Rainfall API returned HTTP ${response.status}`
            );
          }

          const data =
            (await response.json()) as RainfallGeoJSON;

          if (
            !data ||
            data.type !==
              "FeatureCollection" ||
            !Array.isArray(data.features)
          ) {
            throw new Error(
              "Rainfall API returned invalid GeoJSON."
            );
          }

          rainfallGeoJSON =
            data;

          console.log(
            "IMD rainfall loaded successfully."
          );

          console.log(
            "Rainfall features:",
            rainfallGeoJSON.features.length
          );

          setRainfallLoaded(true);
          setRainfallError(null);
        } catch (error) {
          console.error(
            "Rainfall loading error:",
            error
          );

          const message =
            error instanceof Error
              ? error.message
              : "Failed to load IMD rainfall.";

          setRainfallError(
            message
          );
        }

        /* ====================================================
           EXTREME RAINFALL EVENTS
           ==================================================== */

        let extremeEventGeoJSON:
          ExtremeEventGeoJSON = {
            type: "FeatureCollection",
            features: [],
          };

        try {
          const response =
            await extremeEventRequest;

          if (!response.ok) {
            throw new Error(
              `Extreme rainfall API returned HTTP ${response.status}`
            );
          }

          const data =
            (await response.json()) as ExtremeEventGeoJSON;

          if (
            !data ||
            data.type !==
              "FeatureCollection" ||
            !Array.isArray(data.features)
          ) {
            throw new Error(
              "Extreme rainfall API returned invalid GeoJSON."
            );
          }

          extremeEventGeoJSON =
            data;

          console.log(
            "Extreme rainfall events loaded:",
            extremeEventGeoJSON.features.length
          );

          setExtremeEventsLoaded(true);
          setExtremeEventsError(null);
        } catch (error) {
          console.error(
            "Extreme rainfall event loading error:",
            error
          );

          const message =
            error instanceof Error
              ? error.message
              : "Failed to load extreme rainfall events.";

          setExtremeEventsError(
            message
          );
        }

        let riskGeoJSON: RiskGeoJSON = {
          type: "FeatureCollection",
          features: [],
        };

        try {
          const riskResponse =
            await fetch(
              RISK_API,
              {
                cache: "no-store",
              }
            );

          if (!riskResponse.ok) {
            throw new Error(
              `Climate risk API returned HTTP ${riskResponse.status}`
            );
          }

          riskGeoJSON =
            (await riskResponse.json()) as RiskGeoJSON;

          if (
            !riskGeoJSON ||
            riskGeoJSON.type !== "FeatureCollection" ||
            !Array.isArray(riskGeoJSON.features)
          ) {
            throw new Error(
              "Climate risk API returned invalid GeoJSON."
            );
          }

          console.log(
            "Climate risk grid loaded:",
            riskGeoJSON.features.length
          );

          setRiskLoaded(true);
        } catch (error) {
          console.error(
            "Climate risk loading error:",
            error
          );

          setRiskError(
            error instanceof Error
              ? error.message
              : "Failed to load climate risk."
          );
        }

        /* ====================================================
           RAINFALL SOURCE
           ==================================================== */

        map.addSource(
          RAINFALL_SOURCE,
          {
            type: "geojson",

            data: rainfallGeoJSON,
          }
        );

        map.addSource(
          EXTREME_EVENT_SOURCE,
          {
            type: "geojson",

            data: extremeEventGeoJSON,
          }
        );

        if (
          !map.getSource(RISK_SOURCE)
        ) {

          map.addSource(
            RISK_SOURCE,
            {
              type: "geojson",
              data: riskGeoJSON,
            }
          );

        }

        /* ====================================================
           RAINFALL HEATMAP
           
           Heatmap is used at lower zoom levels.
           This makes the IMD field visible even when
           individual 0.25° points are too small.
           ==================================================== */

        map.addLayer({
          id:
            RAINFALL_HEATMAP_LAYER,

          type:
            "heatmap",

          source:
            RAINFALL_SOURCE,

          minzoom:
            2,

          maxzoom:
            7,

          paint: {
            "heatmap-weight": [
              "interpolate",
              ["linear"],
              [
                "coalesce",
                [
                  "get",
                  "rainfall_mm",
                ],
                0,
              ],

              0,
              0,

              1,
              0.08,

              5,
              0.18,

              25,
              0.40,

              50,
              0.60,

              100,
              0.85,

              200,
              1,
            ],

            "heatmap-intensity": [
              "interpolate",
              ["linear"],
              ["zoom"],

              2,
              0.8,

              4,
              1.1,

              6,
              1.5,
            ],

            "heatmap-radius": [
              "interpolate",
              ["linear"],
              ["zoom"],

              2,
              12,

              4,
              20,

              6,
              28,
            ],

            "heatmap-opacity": [
              "interpolate",
              ["linear"],
              ["zoom"],

              2,
              0.72,

              5,
              0.62,

              7,
              0,
            ],

            "heatmap-color": [
              "interpolate",
              ["linear"],
              ["heatmap-density"],

              0,
              "rgba(37,99,235,0)",

              0.08,
              "#2563eb",

              0.20,
              "#06b6d4",

              0.40,
              "#22c55e",

              0.60,
              "#eab308",

              0.78,
              "#f97316",

              0.90,
              "#ef4444",

              1,
              "#991b1b",
            ],
          },
        });

        /* ====================================================
           RAINFALL CIRCLES

           These become the primary visualization when
           zooming into India/state level.
           ==================================================== */

        map.addLayer({
          id:
            RAINFALL_CIRCLE_LAYER,

          type:
            "circle",

          source:
            RAINFALL_SOURCE,

          minzoom:
            3,

          paint: {
            "circle-radius": [
              "interpolate",
              ["linear"],
              [
                "coalesce",
                [
                  "get",
                  "rainfall_mm",
                ],
                0,
              ],

              0,
              2,

              5,
              3,

              25,
              5,

              50,
              7,

              100,
              9,

              200,
              12,
            ],

            "circle-color": [
              "interpolate",
              ["linear"],
              [
                "coalesce",
                [
                  "get",
                  "rainfall_mm",
                ],
                0,
              ],

              0,
              "#2563eb",

              5,
              "#06b6d4",

              20,
              "#22c55e",

              50,
              "#eab308",

              100,
              "#f97316",

              150,
              "#ef4444",

              225,
              "#991b1b",
            ],

            "circle-opacity": [
              "interpolate",
              ["linear"],
              [
                "coalesce",
                [
                  "get",
                  "rainfall_mm",
                ],
                0,
              ],

              0,
              0.18,

              1,
              0.40,

              5,
              0.60,

              25,
              0.75,

              100,
              0.90,

              200,
              1,
            ],

            "circle-stroke-color":
              "#ffffff",

            "circle-stroke-width":
              0.7,

            "circle-stroke-opacity":
              0.45,
          },
        });

        /* ============================================================
           CLIMATE RISK VISUALIZATION
           ============================================================ */

        if (!map.getLayer(RISK_LAYER)) {

          console.log(
            "Adding climate risk layer:",
            {
              source: RISK_SOURCE,
              layer: RISK_LAYER,
              features: riskGeoJSON.features.length,
            }
          );

          map.addLayer({
            id: RISK_LAYER,
            type: "circle",
            source: RISK_SOURCE,
            minzoom: 2,
            maxzoom: 18,
            paint: {
              "circle-radius": [
                "interpolate",
                ["linear"],
                ["zoom"],
                2, 5,
                3, 6,
                4, 7,
                5, 8,
                6, 9,
                8, 11,
                10, 13,
              ],
              "circle-color": [
                "match", ["get", "risk_category"],
                "low", "#22c55e",
                "moderate", "#facc15",
                "high", "#f97316",
                "extreme", "#ef4444",
                "#64748b",
              ],
              "circle-opacity": 0.85,
              "circle-stroke-color": "#111827",
              "circle-stroke-width": 1.5,
              "circle-stroke-opacity": 0.9,
            },
          });

          try {
            map.moveLayer(RISK_LAYER);
          } catch (error) {
            console.warn(
              "Could not move climate risk layer to top:",
              error
            );
          }

          console.log(
            "Climate risk layer ready."
          );
        }

        map.addLayer({
          id: EXTREME_EVENT_LABEL_LAYER,
          type: "circle",
          source: EXTREME_EVENT_SOURCE,
          paint: {
            "circle-radius": [
              "match", ["get", "category"],
              "extremely_heavy", 17,
              "very_heavy", 13,
              "heavy", 10,
              8,
            ],
            "circle-color": "rgba(0,0,0,0)",
            "circle-stroke-color": [
              "match", ["get", "category"],
              "extremely_heavy", "#ff0033",
              "very_heavy", "#ff7a00",
              "heavy", "#ffd000",
              "#ffffff",
            ],
            "circle-stroke-width": 1.5,
            "circle-opacity": 0.65,
          },
        });

        /* ====================================================
           STATE OUTLINE

           Added AFTER rainfall so that boundaries remain
           visible above the rainfall visualization.
           ==================================================== */

        map.addLayer({
          id:
            STATE_OUTLINE_LAYER,

          type:
            "line",

          source:
            STATE_SOURCE,

          paint: {
            "line-color":
              "#0284c7",

            "line-width":
              2,

            "line-opacity":
              0.95,
          },
        });

        /* ====================================================
           SELECTED STATE FILL

           Uses feature-state rather than a property filter.
           ==================================================== */

        map.addLayer({
          id:
            SELECTED_STATE_FILL_LAYER,

          type:
            "fill",

          source:
            STATE_SOURCE,

          paint: {
            "fill-color":
              "#00e5ff",

            "fill-opacity": [
              "case",

              [
                "boolean",
                [
                  "feature-state",
                  "selected",
                ],
                false,
              ],

              0.42,

              0,
            ],
          },
        });

        /* ====================================================
           SELECTED STATE OUTLINE
           ==================================================== */

        map.addLayer({
          id:
            SELECTED_STATE_OUTLINE_LAYER,

          type:
            "line",

          source:
            STATE_SOURCE,

          paint: {
            "line-color":
              "#00ffff",

            "line-width": [
              "case",

              [
                "boolean",
                [
                  "feature-state",
                  "selected",
                ],
                false,
              ],

              5,

              0,
            ],

            "line-opacity": [
              "case",

              [
                "boolean",
                [
                  "feature-state",
                  "selected",
                ],
                false,
              ],

              1,

              0,
            ],
          },
        });

        /* ====================================================
           INITIAL INDIA VIEW
           ==================================================== */

        map.fitBounds(
          [
            [68.0, 6.0],
            [97.5, 37.5],
          ],
          {
            padding: 35,

            duration: 0,

            maxZoom: 5,
          }
        );

        /* ====================================================
           STATE HOVER
           ==================================================== */

        map.on(
          "mouseenter",
          STATE_FILL_LAYER,
          () => {
            map.getCanvas().style.cursor =
              "pointer";
          }
        );

        map.on(
          "mouseleave",
          STATE_FILL_LAYER,
          () => {
            map.getCanvas().style.cursor =
              "";
          }
        );

        /* ====================================================
           RAINFALL HOVER
           ==================================================== */

        map.on(
          "mouseenter",
          RAINFALL_CIRCLE_LAYER,
          () => {
            map.getCanvas().style.cursor =
              "crosshair";
          }
        );

        map.on(
          "mouseleave",
          RAINFALL_CIRCLE_LAYER,
          () => {
            map.getCanvas().style.cursor =
              "";
          }
        );

        map.on(
          "mouseenter",
          RISK_LAYER,
          () => {
            map.getCanvas().style.cursor =
              "pointer";
          }
        );

        map.on(
          "mouseleave",
          RISK_LAYER,
          () => {
            map.getCanvas().style.cursor =
              "";
          }
        );

        map.on(
          "mouseenter",
          EXTREME_EVENT_LAYER,
          () => {
            map.getCanvas().style.cursor =
              "pointer";
          }
        );

        map.on(
          "mouseleave",
          EXTREME_EVENT_LAYER,
          () => {
            map.getCanvas().style.cursor =
              "";
          }
        );

        /* ====================================================
           STATE CLICK

           IMPORTANT:
           We no longer perform Turf
           booleanPointInPolygon() for every click.

           MapLibre already knows which state feature
           was clicked.
           ==================================================== */

        map.on(
          "click",
          STATE_FILL_LAYER,
          (event) => {
            if (
              !event.features ||
              event.features.length === 0
            ) {
              return;
            }

            /*
             * Prevent rainfall clicks from selecting
             * the state underneath.
             */

            const rainfallFeatures =
              map.queryRenderedFeatures(
                event.point,
                {
                  layers: [
                    RAINFALL_CIRCLE_LAYER,
                  ],
                }
              );

            const riskFeatures =
              map.queryRenderedFeatures(
                event.point,
                {
                  layers: [
                    RISK_LAYER,
                  ],
                }
              );

            if (
              rainfallFeatures.length > 0 ||
              riskFeatures.length > 0
            ) {
              return;
            }

            const clickedFeature =
              event.features[0];

            const featureId =
              clickedFeature.id;

            if (
              featureId === undefined ||
              featureId === null
            ) {
              console.warn(
                "Clicked state has no feature ID."
              );

              return;
            }

            const numericOrStringId =
              featureId as
                | number
                | string;

            const originalFeature =
              statesRef.current?.features.find(
                (feature) =>
                  feature.id ===
                  numericOrStringId
              );

            if (!originalFeature) {
              console.warn(
                "Could not find selected state feature."
              );

              return;
            }

            const stateName =
              originalFeature.properties
                ?.__stateName ??
              "Unknown State";

            console.log(
              "STATE SELECTED:",
              stateName
            );

            console.log(
              "STATE ID:",
              numericOrStringId
            );

            /* ==================================================
               CLEAR PREVIOUS SELECTION
               ================================================== */

            if (
              selectedStateIdRef.current !==
              null
            ) {
              map.setFeatureState(
                {
                  source:
                    STATE_SOURCE,

                  id:
                    selectedStateIdRef.current,
                },
                {
                  selected:
                    false,
                }
              );
            }

            /* ==================================================
               SET NEW SELECTION
               ================================================== */

            map.setFeatureState(
              {
                source:
                  STATE_SOURCE,

                id:
                  numericOrStringId,
              },
              {
                selected:
                  true,
              }
            );

            selectedStateIdRef.current =
              numericOrStringId;

            console.log(
              "STATE HIGHLIGHT APPLIED:",
              stateName
            );

            /* ==================================================
               SEND TO PARENT
               ================================================== */

            onStateSelectRef.current?.(
              stateName
            );

            /* ==================================================
               ZOOM TO STATE
               ================================================== */

            try {
              const bounds =
                turf.bbox(
                  originalFeature as Feature<
                    Polygon | MultiPolygon,
                    StateProperties
                  >
                );

              map.fitBounds(
                [
                  [
                    bounds[0],
                    bounds[1],
                  ],

                  [
                    bounds[2],
                    bounds[3],
                  ],
                ],
                {
                  padding: {
                    top: 90,
                    bottom: 90,
                    left: 90,
                    right: 90,
                  },

                  maxZoom: 7,

                  duration:
                    1000,

                  essential:
                    true,
                }
              );

              console.log(
                "ZOOMING TO STATE:",
                stateName
              );
            } catch (error) {
              console.error(
                "State zoom failed:",
                error
              );
            }
          }
        );

        /* ====================================================
           RAINFALL CLICK
           ==================================================== */

        map.on(
          "click",
          RAINFALL_CIRCLE_LAYER,
          (event) => {
            if (
              !event.features ||
              event.features.length === 0
            ) {
              return;
            }

            const feature =
              event.features[0];

            const properties =
              feature.properties as
                | RainfallProperties
                | undefined;

            if (!properties) {
              return;
            }

            const rainfall =
              Number(
                properties.rainfall_mm
              );

            const date =
              properties.date ??
              RAINFALL_DATE;

            const rainfallText =
              Number.isFinite(
                rainfall
              )
                ? rainfall.toFixed(2)
                : "N/A";

            new Popup({
              closeButton: true,

              closeOnClick: true,

              maxWidth:
                "260px",
            })
              .setLngLat(
                event.lngLat
              )
              .setHTML(
                `
                  <div
                    style="
                      min-width:160px;
                      font-family:Arial,sans-serif;
                    "
                  >
                    <div
                      style="
                        font-size:11px;
                        font-weight:700;
                        letter-spacing:.08em;
                        margin-bottom:8px;
                      "
                    >
                      IMD RAINFALL
                    </div>

                    <div
                      style="
                        font-size:22px;
                        font-weight:700;
                        margin-bottom:6px;
                      "
                    >
                      ${rainfallText} mm
                    </div>

                    <div
                      style="
                        font-size:11px;
                        opacity:.7;
                      "
                    >
                      Date: ${date}
                    </div>

                    <div
                      style="
                        font-size:10px;
                        opacity:.6;
                        margin-top:4px;
                      "
                    >
                      Source: IMD
                    </div>
                  </div>
                `
              )
              .addTo(map);
          }
        );

        map.on(
          "click",
          RISK_LAYER,
          (event) => {
            const features =
              map.queryRenderedFeatures(
                event.point,
                {
                  layers: [
                    RISK_LAYER,
                  ],
                }
              );

            if (
              !features.length
            ) {
              return;
            }

            const properties =
              features[0]
                .properties as RiskProperties;

            const rainfall =
              Number(
                properties.rainfall_mm
              );

            const score =
              Number(
                properties.hazard_score
              );

            const category =
              properties.risk_category ??
              "unknown";

            const rainfallCategory =
              properties.rainfall_category ??
              "unknown";

            const coordinates =
              (features[0].geometry as GeoJSON.Point)
                .coordinates;

            new Popup({
              closeButton: true,
              closeOnClick: true,
              maxWidth: "320px",
            })
              .setLngLat([
                coordinates[0],
                coordinates[1],
              ])
              .setHTML(`
                <div style="
                  font-family: sans-serif;
                  min-width: 210px;
                ">

                  <div style="
                    font-size: 11px;
                    font-weight: 700;
                    letter-spacing: 0.08em;
                    margin-bottom: 8px;
                  ">
                    CLIMATE RISK
                  </div>

                  <div style="
                    font-size: 16px;
                    font-weight: 800;
                    margin-bottom: 8px;
                  ">
                    ${category.toUpperCase()}
                  </div>

                  <div>
                    Rainfall:
                    <strong>
                      ${
                        Number.isFinite(rainfall)
                          ? rainfall.toFixed(2)
                          : "N/A"
                      } mm
                    </strong>
                  </div>

                  <div>
                    Hazard Score:
                    <strong>
                      ${
                        Number.isFinite(score)
                          ? score.toFixed(2)
                          : "N/A"
                      }
                    </strong>
                  </div>

                  <div>
                    Rainfall Category:
                    <strong>
                      ${rainfallCategory}
                    </strong>
                  </div>

                </div>
              `)
              .addTo(map);
          }
        );

          /* ====================================================
             EXTREME RAINFALL EVENT CLICK
             ==================================================== */

          map.on(
            "click",
            EXTREME_EVENT_LAYER,
            (event) => {
              if (
                !event.features ||
                event.features.length === 0
              ) {
                return;
              }

              event.originalEvent.stopPropagation();

              const feature =
                event.features[0];

              const properties =
                feature.properties as
                  | ExtremeEventProperties
                  | undefined;

              if (!properties) {
                return;
              }

              const rainfall =
                Number(
                  properties.rainfall_mm
                );

              const category =
                properties.category ??
                "unknown";

              const date =
                properties.date ??
                RAINFALL_DATE;

              const rainfallText =
                Number.isFinite(rainfall)
                  ? rainfall.toFixed(2)
                  : "N/A";

              const categoryText =
                category
                  .replaceAll("_", " ")
                  .toUpperCase();

              new Popup({
                closeButton: true,

                closeOnClick: true,

                maxWidth:
                  "280px",
              })
                .setLngLat(
                  event.lngLat
                )
                .setHTML(
                  `
                    <div
                      style="
                        min-width:190px;
                        font-family:Arial,sans-serif;
                      "
                    >
                      <div
                        style="
                          font-size:11px;
                          font-weight:700;
                          letter-spacing:.08em;
                          margin-bottom:8px;
                        "
                      >
                        EXTREME RAINFALL EVENT
                      </div>

                      <div
                        style="
                          font-size:24px;
                          font-weight:800;
                          margin-bottom:6px;
                        "
                      >
                        ${rainfallText} mm
                      </div>

                      <div
                        style="
                          font-size:12px;
                          font-weight:700;
                          margin-bottom:8px;
                        "
                      >
                        ${categoryText}
                      </div>

                      <div
                        style="
                          font-size:11px;
                          opacity:.75;
                        "
                      >
                        Date: ${date}
                      </div>

                      <div
                        style="
                          font-size:10px;
                          opacity:.6;
                          margin-top:5px;
                        "
                      >
                        Source: IMD
                      </div>
                    </div>
                  `
                )
                .addTo(map);
            }
          );

        /* ====================================================
           MAP READY
           ==================================================== */

        /* ============================================================
           FINAL CLIMATE RISK LAYER ORDER

           Risk must be moved after all other scientific and boundary
           layers have been created.
           ============================================================ */

        if (map.getLayer(RISK_LAYER)) {

          map.setLayoutProperty(
            RISK_LAYER,
            "visibility",
            "visible"
          );

          map.moveLayer(
            RISK_LAYER
          );

          console.log(
            "Climate risk layer moved to FINAL TOP position."
          );

          console.log(
            "FINAL risk layer index:",
            map
              .getStyle()
              ?.layers
              ?.findIndex(
                (layer) =>
                  layer.id === RISK_LAYER
              )
          );

          console.log(
            "FINAL map layers:",
            map
              .getStyle()
              ?.layers
              ?.map(
                (layer) => layer.id
              )
              .slice(-10)
          );

        }

        if (!cancelled) {
          setMapReady(true);
        }

        console.log(
          "India state boundaries loaded successfully."
        );

        console.log(
          "IMD rainfall layer ready."
        );

        console.log(
          "Risk source exists:",
          !!map.getSource(RISK_SOURCE)
        );

        console.log(
          "Risk layer exists:",
          !!map.getLayer(RISK_LAYER)
        );

        console.log(
          "Risk layer visibility:",
          map.getLayoutProperty(
            RISK_LAYER,
            "visibility"
          )
        );

        console.log(
          "Map zoom:",
          map.getZoom()
        );

        console.log(
          "Map center:",
          map.getCenter()
        );
      } catch (error) {
        console.error(
          "Map initialization error:",
          error
        );

        if (!cancelled) {
          setMapError(
            error instanceof Error
              ? error.message
              : "Failed to initialize map."
          );
        }
      }
    });

    /* ========================================================
       RESPONSIVE RESIZE
       ======================================================== */

    const resizeObserver =
      new ResizeObserver(() => {
        map.resize();
      });

    resizeObserver.observe(
      containerRef.current
    );

    /* ========================================================
       CLEANUP
       ======================================================== */

    return () => {
      cancelled = true;

      resizeObserver.disconnect();

      console.log(
        "Cleaning up MapView..."
      );

      if (
        selectedStateIdRef.current !==
        null
      ) {
        try {
          map.setFeatureState(
            {
              source:
                STATE_SOURCE,

              id:
                selectedStateIdRef.current,
            },
            {
              selected:
                false,
            }
          );
        } catch {
          // Map may already be destroyed.
        }
      }

      selectedStateIdRef.current =
        null;

      statesRef.current = null;

      map.remove();

      mapRef.current = null;
    };
  }, []);

  /* ==========================================================
     UI
     ========================================================== */

  return (
    <div
      style={{
        position: "relative",

        width: "100%",

        height: "100%",

        minHeight: "500px",

        overflow: "hidden",

        borderRadius: "8px",
      }}
    >
      {/* ====================================================
          MAP CONTAINER
          ==================================================== */}

      <div
        ref={containerRef}
        style={{
          position: "absolute",

          inset: 0,

          width: "100%",

          height: "100%",
        }}
      />

      {/* ====================================================
          LOADING
          ==================================================== */}

      {!mapReady &&
        !mapError && (
          <div
            style={{
              position:
                "absolute",

              inset: 0,

              zIndex: 20,

              display:
                "flex",

              alignItems:
                "center",

              justifyContent:
                "center",

              background:
                "rgba(2,8,15,.55)",

              color:
                "#ffffff",

              fontSize:
                "12px",

              fontWeight:
                700,

              letterSpacing:
                ".08em",
            }}
          >
            LOADING INDIA CLIMATE MAP...
          </div>
        )}

      {/* ====================================================
          MAP ERROR
          ==================================================== */}

      {mapError && (
        <div
          style={{
            position:
              "absolute",

            top:
              "14px",

            left:
              "14px",

            right:
              "14px",

            zIndex:
              30,

            padding:
              "12px 14px",

            borderRadius:
              "7px",

            background:
              "rgba(127,29,29,.92)",

            color:
              "#ffffff",

            fontSize:
              "12px",
          }}
        >
          Map error: {mapError}
        </div>
      )}

      {/* ====================================================
          IMD STATUS
          ==================================================== */}

      {mapReady && (
        <div
          style={{
            position:
              "absolute",

            top:
              "14px",

            left:
              "14px",

            zIndex:
              10,

            padding:
              "9px 12px",

            borderRadius:
              "7px",

            background:
              "rgba(0,0,0,.76)",

            color:
              "#ffffff",

            backdropFilter:
              "blur(7px)",

            fontSize:
              "11px",

            fontWeight:
              700,

            letterSpacing:
              ".05em",
          }}
        >
          IMD RAINFALL

          <div
            style={{
              marginTop:
                "4px",

              fontSize:
                "10px",

              fontWeight:
                400,

              opacity:
                0.75,
            }}
          >
            {RAINFALL_DATE}

            {" • "}

            {rainfallLoaded
              ? "DATA LOADED"
              : rainfallError
                ? "ERROR"
                : "LOADING"}
          </div>

            <div
              style={{
                marginTop:
                  "4px",

                fontSize:
                  "10px",

                fontWeight:
                  400,

                opacity:
                  0.75,
              }}
            >
              EXTREME EVENTS:{" "}

              {extremeEventsLoaded
                ? "122 EVENTS"
                : extremeEventsError
                  ? "ERROR"
                  : "LOADING"}
            </div>
        </div>
      )}

      {/* ====================================================
          RAINFALL ERROR
          ==================================================== */}

      {rainfallError && (
        <div
          style={{
            position:
              "absolute",

            left:
              "14px",

            bottom:
              "50px",

            zIndex:
              10,

            maxWidth:
              "280px",

            padding:
              "8px 10px",

            borderRadius:
              "6px",

            background:
              "rgba(127,29,29,.88)",

            color:
              "#ffffff",

            fontSize:
              "10px",
          }}
        >
          IMD rainfall unavailable:
          {" "}
          {rainfallError}
        </div>
      )}

      {/* ====================================================
          RAINFALL LEGEND
          ==================================================== */}

      {rainfallLoaded && (
        <div
          style={{
            position:
              "absolute",

            right:
              "14px",

            bottom:
              "50px",

            zIndex:
              10,

            width:
              "190px",

            padding:
              "12px",

            borderRadius:
              "8px",

            background:
              "rgba(0,0,0,.80)",

            color:
              "#ffffff",

            backdropFilter:
              "blur(7px)",

            fontSize:
              "10px",
          }}
        >
          <div
            style={{
              fontWeight:
                700,

              letterSpacing:
                ".08em",

              marginBottom:
                "8px",
            }}
          >
            DAILY RAINFALL
          </div>

          <div
            style={{
              height:
                "10px",

              width:
                "100%",

              borderRadius:
                "5px",

              background:
                "linear-gradient(to right, #2563eb, #06b6d4, #22c55e, #eab308, #f97316, #ef4444, #991b1b)",
            }}
          />

          <div
            style={{
              display:
                "flex",

              justifyContent:
                "space-between",

              marginTop:
                "5px",

              opacity:
                0.8,
            }}
          >
            <span>0 mm</span>

            <span>25</span>

            <span>50</span>

            <span>100</span>

            <span>200+</span>
          </div>
        </div>
      )}
    </div>
  );
}