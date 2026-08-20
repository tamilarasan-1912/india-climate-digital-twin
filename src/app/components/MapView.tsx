"use client";

import React, {
  useEffect,
  useRef,
  useState,
} from "react";

import {
  Map,
  NavigationControl,
} from "maplibre-gl";

import "maplibre-gl/dist/maplibre-gl.css";

import * as turf from "@turf/turf";

import type {
  FeatureCollection,
  Feature,
  Geometry,
  GeoJsonProperties,
} from "geojson";

interface MapViewProps {
  onStateSelect?: (stateName: string) => void;
}

export default function MapView({
  onStateSelect,
}: MapViewProps) {
  // =========================================================
  // REFERENCES
  // =========================================================

  const mapContainerRef =
    useRef<HTMLDivElement | null>(null);

  const mapRef =
    useRef<Map | null>(null);

  const geoJsonDataRef =
    useRef<FeatureCollection | null>(null);

  const selectedStateIdRef =
    useRef<number | null>(null);

  const onStateSelectRef =
    useRef(onStateSelect);

  // =========================================================
  // REACT STATE
  // =========================================================

  const [isLoaded, setIsLoaded] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  // =========================================================
  // KEEP CALLBACK UPDATED
  // =========================================================

  useEffect(() => {
    onStateSelectRef.current =
      onStateSelect;
  }, [onStateSelect]);

  // =========================================================
  // STATE NAME HELPER
  // =========================================================

  const getFeatureName = (
    properties: GeoJsonProperties
  ): string => {
    if (!properties) {
      return "Unknown State";
    }

    return (
      properties.shapeName ||
      properties.shapeName_en ||
      properties.NAME_1 ||
      properties.NAME_1_EN ||
      properties.name ||
      properties.NAME ||
      properties.st_nm ||
      properties.ST_NM ||
      properties.state ||
      properties.State ||
      properties.STATE ||
      "Unknown State"
    );
  };

  // =========================================================
  // MAP INITIALIZATION
  // =========================================================

  useEffect(() => {
    if (!mapContainerRef.current) {
      return;
    }

    // Prevent duplicate map initialization
    // during Next.js development/HMR.
    if (mapRef.current) {
      return;
    }

    console.log(
      "Initializing MapLibre..."
    );

    // =======================================================
    // CREATE MAP
    // =======================================================

    const map = new Map({
      container:
        mapContainerRef.current,

      style: {
        version: 8,

        sources: {},

        layers: [],
      },

      center: [
        78.9629,
        20.5937,
      ],

      zoom: 3.5,

      minZoom: 2,

      maxZoom: 18,
    });

    mapRef.current = map;

    // =======================================================
    // NAVIGATION CONTROL
    // =======================================================

    map.addControl(
      new NavigationControl({
        visualizePitch: true,
      }),
      "top-right"
    );

    // =======================================================
    // MAP LOAD
    // =======================================================

    map.on(
      "load",
      async () => {
        console.log(
          "MapLibre India map loaded."
        );

        try {
          // =================================================
          // 1. OPENSTREETMAP BASEMAP
          // =================================================

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

          // =================================================
          // 2. LOAD INDIA GEOJSON
          // =================================================

          const response =
            await fetch(
              "/data/india/india-states.geojson",
              {
                cache: "no-store",
              }
            );

          if (!response.ok) {
            throw new Error(
              `India GeoJSON request failed with HTTP ${response.status}`
            );
          }

          const rawGeoJson =
            (await response.json()) as FeatureCollection;

          // =================================================
          // 3. VALIDATE GEOJSON
          // =================================================

          if (
            !rawGeoJson ||
            rawGeoJson.type !==
              "FeatureCollection"
          ) {
            throw new Error(
              "Invalid India GeoJSON. Expected FeatureCollection."
            );
          }

          if (
            !Array.isArray(
              rawGeoJson.features
            )
          ) {
            throw new Error(
              "Invalid India GeoJSON. Features array is missing."
            );
          }

          // =================================================
          // 4. ASSIGN SAFE INTERNAL IDS
          // =================================================

          /*
           * The original shapeID values are very large.
           *
           * Example:
           *
           * 1811400B21167269026319
           *
           * We do NOT use those as MapLibre IDs.
           *
           * Instead:
           *
           * 0
           * 1
           * 2
           * ...
           * 35
           *
           * The original properties remain untouched.
           */

          const processedFeatures =
            rawGeoJson.features.map(
              (
                feature,
                index
              ) => ({
                ...feature,

                id: index,
              })
            );

          const processedGeoJson: FeatureCollection =
            {
              ...rawGeoJson,

              features:
                processedFeatures,
            };

          geoJsonDataRef.current =
            processedGeoJson;

          console.log(
            "India GeoJSON loaded successfully."
          );

          console.log(
            "Number of features:",
            processedGeoJson
              .features.length
          );

          // =================================================
          // 5. ADD INDIA STATE SOURCE
          // =================================================

          map.addSource(
            "india-states",
            {
              type: "geojson",

              data:
                processedGeoJson,
            }
          );

          // =================================================
          // 6. NORMAL STATE FILL
          // =================================================

          map.addLayer({
            id:
              "india-states-fill",

            type: "fill",

            source:
              "india-states",

            paint: {
              "fill-color":
                "#38bdf8",

              "fill-opacity":
                0.08,
            },
          });

          // =================================================
          // 7. NORMAL STATE BOUNDARIES
          // =================================================

          map.addLayer({
            id:
              "india-states-outline",

            type: "line",

            source:
              "india-states",

            paint: {
              "line-color":
                "#075985",

              "line-width":
                2.5,

              "line-opacity":
                1,
            },
          });

          // =================================================
          // 8. SELECTED STATE FILL
          // =================================================

          /*
           * This layer is deliberately separate from the
           * normal state fill.
           *
           * It is placed AFTER the normal state layers,
           * so the selected state is guaranteed to appear
           * on top.
           *
           * Initially the filter matches nothing.
           */

          map.addLayer({
            id:
              "selected-state-fill",

            type: "fill",

            source:
              "india-states",

            filter: [
              "==",
              ["id"],
              -1,
            ],

            paint: {
              "fill-color":
                "#00e5ff",

              "fill-opacity":
                0.72,
            },
          });

          // =================================================
          // 9. SELECTED STATE BORDER
          // =================================================

          map.addLayer({
            id:
              "selected-state-outline",

            type: "line",

            source:
              "india-states",

            filter: [
              "==",
              ["id"],
              -1,
            ],

            paint: {
              "line-color":
                "#00ffff",

              "line-width":
                6,

              "line-opacity":
                1,

              "line-blur":
                0,
            },
          });

          console.log(
            "India state boundaries loaded successfully."
          );

          console.log(
            "Selected-state filter layers ready."
          );

          setIsLoaded(true);

          // =================================================
          // 10. HOVER CURSOR
          // =================================================

          map.on(
            "mouseenter",
            "india-states-fill",
            () => {
              map
                .getCanvas()
                .style.cursor =
                "pointer";
            }
          );

          map.on(
            "mouseleave",
            "india-states-fill",
            () => {
              map
                .getCanvas()
                .style.cursor =
                "";
            }
          );

          // =================================================
          // 11. MAP CLICK
          // =================================================

          map.on(
            "click",
            (event) => {
              console.log(
                "================================"
              );

              console.log(
                "MAP CLICK DETECTED"
              );

              console.log(
                "Clicked coordinates:",
                {
                  lng:
                    event.lngLat.lng,

                  lat:
                    event.lngLat.lat,
                }
              );

              console.log(
                "================================"
              );

              const geoJson =
                geoJsonDataRef.current;

              if (!geoJson) {
                console.warn(
                  "India GeoJSON is not available."
                );

                return;
              }

              // =============================================
              // CREATE TURF POINT
              // =============================================

              const clickPoint =
                turf.point([
                  event.lngLat.lng,
                  event.lngLat.lat,
                ]);

              // =============================================
              // FIND STATE
              // =============================================

              let foundFeature:
                Feature<
                  Geometry,
                  GeoJsonProperties
                > | null = null;

              for (
                const feature of
                  geoJson.features
              ) {
                if (
                  !feature.geometry
                ) {
                  continue;
                }

                const geometryType =
                  feature.geometry
                    .type;

                if (
                  geometryType !==
                    "Polygon" &&
                  geometryType !==
                    "MultiPolygon"
                ) {
                  continue;
                }

                try {
                  const inside =
                    turf.booleanPointInPolygon(
                      clickPoint,

                      feature as Feature<
                        | "Polygon"
                        | "MultiPolygon",
                        GeoJsonProperties
                      >
                    );

                  if (inside) {
                    foundFeature =
                      feature;

                    break;
                  }
                } catch (
                  geometryError
                ) {
                  console.warn(
                    "Geometry check failed:",
                    geometryError
                  );
                }
              }

              // =============================================
              // NO STATE
              // =============================================

              if (
                !foundFeature
              ) {
                console.log(
                  "No India state at this click."
                );

                return;
              }

              // =============================================
              // SAFE ID
              // =============================================

              if (
                typeof foundFeature.id !==
                "number"
              ) {
                console.warn(
                  "Selected feature does not have a numeric ID."
                );

                return;
              }

              const stateId =
                foundFeature.id;

              // =============================================
              // STATE NAME
              // =============================================

              const stateName =
                getFeatureName(
                  foundFeature.properties
                );

              // =============================================
              // DEBUG
              // =============================================

              console.log(
                "Selected state properties:",
                foundFeature.properties
              );

              console.log(
                "SELECTED STATE:",
                stateName
              );

              console.log(
                "SELECTED STATE ID:",
                stateId
              );

              // =============================================
              // REMOVE OLD FILTER
              // =============================================

              /*
               * Reset both selected layers first.
               */

              if (
                map.getLayer(
                  "selected-state-fill"
                )
              ) {
                map.setFilter(
                  "selected-state-fill",
                  [
                    "==",
                    ["id"],
                    -1,
                  ]
                );
              }

              if (
                map.getLayer(
                  "selected-state-outline"
                )
              ) {
                map.setFilter(
                  "selected-state-outline",
                  [
                    "==",
                    ["id"],
                    -1,
                  ]
                );
              }

              // =============================================
              // APPLY NEW FILTER
              // =============================================

              if (
                map.getLayer(
                  "selected-state-fill"
                )
              ) {
                map.setFilter(
                  "selected-state-fill",
                  [
                    "==",
                    ["id"],
                    stateId,
                  ]
                );
              }

              if (
                map.getLayer(
                  "selected-state-outline"
                )
              ) {
                map.setFilter(
                  "selected-state-outline",
                  [
                    "==",
                    ["id"],
                    stateId,
                  ]
                );
              }

              // =============================================
              // SAVE SELECTED ID
              // =============================================

              selectedStateIdRef.current =
                stateId;

              console.log(
                "STATE FILTER APPLIED:",
                stateName
              );

              console.log(
                "SELECTED STATE SHOULD NOW BE CYAN."
              );

              // =============================================
              // SEND STATE TO PAGE.TSX
              // =============================================

              if (
                onStateSelectRef.current
              ) {
                onStateSelectRef.current(
                  stateName
                );
              }

              // =============================================
              // ZOOM TO STATE
              // =============================================

              try {
                console.log(
                  "ZOOMING TO STATE:",
                  stateName
                );

                const bounds =
                  turf.bbox(
                    foundFeature
                  );

                const [
                  minX,
                  minY,
                  maxX,
                  maxY,
                ] = bounds;

                map.fitBounds(
                  [
                    [
                      minX,
                      minY,
                    ],

                    [
                      maxX,
                      maxY,
                    ],
                  ],

                  {
                    padding: {
                      top: 80,

                      bottom: 80,

                      left: 80,

                      right: 80,
                    },

                    maxZoom: 7,

                    duration: 1000,

                    essential: true,
                  }
                );
              } catch (
                zoomError
              ) {
                console.warn(
                  "Could not zoom to state:",
                  zoomError
                );
              }
            }
          );
        } catch (
          loadingError
        ) {
          console.error(
            "Error loading India map data:",
            loadingError
          );

          const message =
            loadingError instanceof
            Error
              ? loadingError.message
              : "Failed to load India map data.";

          setError(message);
        }
      }
    );

    // =======================================================
    // MAP ERROR HANDLER
    // =======================================================

    map.on(
      "error",
      (event: any) => {
        console.error(
          "MapLibre error:",
          event?.error ||
            event
        );
      }
    );

    // =======================================================
    // CLEANUP
    // =======================================================

    return () => {
      console.log(
        "Cleaning up MapView..."
      );

      selectedStateIdRef.current =
        null;

      geoJsonDataRef.current =
        null;

      if (mapRef.current) {
        mapRef.current.remove();

        mapRef.current =
          null;
      }
    };
  }, []);

  // =========================================================
  // RENDER
  // =========================================================

  return (
    <div
      style={{
        position:
          "relative",

        width:
          "100%",

        height:
          "100%",

        minHeight:
          "500px",

        overflow:
          "hidden",

        borderRadius:
          "8px",
      }}
    >
      {/* =====================================================
          MAP
          ===================================================== */}

      <div
        ref={mapContainerRef}
        style={{
          width:
            "100%",

          height:
            "100%",
        }}
      />

      {/* =====================================================
          LOADING
          ===================================================== */}

      {!isLoaded &&
        !error && (
          <div
            style={{
              position:
                "absolute",

              inset:
                0,

              display:
                "flex",

              alignItems:
                "center",

              justifyContent:
                "center",

              background:
                "rgba(0, 0, 0, 0.40)",

              color:
                "#ffffff",

              fontSize:
                "14px",

              fontWeight:
                600,

              letterSpacing:
                "0.08em",

              zIndex:
                10,
            }}
          >
            LOADING INDIA CLIMATE MAP...
          </div>
        )}

      {/* =====================================================
          ERROR
          ===================================================== */}

      {error && (
        <div
          style={{
            position:
              "absolute",

            inset:
              0,

            display:
              "flex",

            flexDirection:
              "column",

            alignItems:
              "center",

            justifyContent:
              "center",

            padding:
              "24px",

            background:
              "rgba(80, 0, 0, 0.80)",

            color:
              "#ffffff",

            textAlign:
              "center",

            zIndex:
              20,
          }}
        >
          <div
            style={{
              fontSize:
                "16px",

              fontWeight:
                700,

              marginBottom:
                "10px",
            }}
          >
            MAP DATA ERROR
          </div>

          <div
            style={{
              maxWidth:
                "600px",

              fontSize:
                "13px",

              lineHeight:
                1.6,

              opacity:
                0.9,
            }}
          >
            {error}
          </div>
        </div>
      )}
    </div>
  );
}