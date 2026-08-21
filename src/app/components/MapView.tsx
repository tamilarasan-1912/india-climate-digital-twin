"use client";

import { useEffect, useRef, useState } from "react";

import {
  Map,
  NavigationControl,
  Popup,
  type GeoJSONSource,
} from "maplibre-gl";

import "maplibre-gl/dist/maplibre-gl.css";

import * as turf from "@turf/turf";

import type {
  FeatureCollection,
  Feature,
  Geometry,
  GeoJsonProperties,
} from "geojson";

/*
 * ============================================================
 * TYPES
 * ============================================================
 */

interface MapViewProps {
  onStateSelect?: (stateName: string) => void;
}

interface RainfallFeature {
  type: "Feature";

  geometry: {
    type: "Point";

    coordinates: [
      number,
      number
    ];
  };

  properties: {
    rainfall_mm: number;

    date: string;
  };
}

interface RainfallGeoJSON {
  type: "FeatureCollection";

  features: RainfallFeature[];
}


/*
 * ============================================================
 * COMPONENT
 * ============================================================
 */

export default function MapView({
  onStateSelect,
}: MapViewProps) {

  /*
   * ==========================================================
   * REFERENCES
   * ==========================================================
   */

  const mapContainerRef =
    useRef<HTMLDivElement | null>(null);

  const mapRef =
    useRef<Map | null>(null);

  const geoJsonDataRef =
    useRef<FeatureCollection | null>(null);

  const onStateSelectRef =
    useRef(onStateSelect);


  /*
   * ==========================================================
   * STATE
   * ==========================================================
   */

  const [isLoaded, setIsLoaded] =
    useState(false);

  const [isRainfallLoaded, setIsRainfallLoaded] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const [rainfallError, setRainfallError] =
    useState<string | null>(null);

  /*
   * We are currently using the verified
   * IMD 2024 dataset.
   */
  const rainfallDate =
    "2024-07-15";


  /*
   * ==========================================================
   * CALLBACK REF
   * ==========================================================
   */

  useEffect(() => {

    onStateSelectRef.current =
      onStateSelect;

  }, [onStateSelect]);


  /*
   * ==========================================================
   * STATE NAME HELPER
   * ==========================================================
   */

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


  /*
   * ==========================================================
   * MAP INITIALIZATION
   * ==========================================================
   */

  useEffect(() => {

    if (!mapContainerRef.current) {
      return;
    }

    if (mapRef.current) {
      return;
    }


    console.log(
      "Initializing MapLibre..."
    );


    /*
     * ========================================================
     * CREATE MAP
     * ========================================================
     */

    const map =
      new Map({

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


    mapRef.current =
      map;


    /*
     * ========================================================
     * NAVIGATION CONTROL
     * ========================================================
     */

    map.addControl(
      new NavigationControl({
        visualizePitch: true,
      }),
      "top-right"
    );


    /*
     * ========================================================
     * MAP LOAD
     * ========================================================
     */

    map.on(
      "load",
      async () => {

        console.log(
          "MapLibre India map loaded."
        );


        try {

          /*
           * ==================================================
           * OSM BASEMAP
           * ==================================================
           */

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

            id:
              "osm-layer",

            type:
              "raster",

            source:
              "osm-basemap",

            minzoom:
              0,

            maxzoom:
              19,

          });


          /*
           * ==================================================
           * INDIA GEOJSON
           * ==================================================
           */

          const response =
            await fetch(
              "/data/india/india-states.geojson",
              {
                cache:
                  "no-store",
              }
            );


          if (!response.ok) {

            throw new Error(
              `India GeoJSON request failed with HTTP ${response.status}`
            );

          }


          const rawGeoJson =
            (await response.json()) as FeatureCollection;


          /*
           * ==================================================
           * VALIDATE GEOJSON
           * ==================================================
           */

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


          /*
           * ==================================================
           * ASSIGN INTERNAL FEATURE IDS
           * ==================================================
           */

          const processedFeatures =
            rawGeoJson.features.map(
              (
                feature,
                index
              ) => ({
                ...feature,

                id:
                  index,
              })
            );


          const processedGeoJson:
            FeatureCollection =
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
            processedGeoJson.features.length
          );


          /*
           * ==================================================
           * INDIA STATE SOURCE
           * ==================================================
           */

          map.addSource(
            "india-states",
            {
              type: "geojson",

              data:
                processedGeoJson,
            }
          );


          /*
           * ==================================================
           * STATE FILL
           * ==================================================
           */

          map.addLayer({

            id:
              "india-states-fill",

            type:
              "fill",

            source:
              "india-states",

            paint: {

              "fill-color":
                "#38bdf8",

              "fill-opacity":
                0.08,

            },

          });


          /*
           * ==================================================
           * STATE BOUNDARIES
           * ==================================================
           */

          map.addLayer({

            id:
              "india-states-outline",

            type:
              "line",

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


          /*
           * ==================================================
           * SELECTED STATE FILL
           * ==================================================
           */

          map.addLayer({

            id:
              "selected-state-fill",

            type:
              "fill",

            source:
              "india-states",

            filter: [
              "==",
              [
                "get",
                "shapeName",
              ],
              "__NO_STATE__",
            ],

            paint: {

              "fill-color":
                "#00e5ff",

              "fill-opacity":
                0.72,

            },

          });


          /*
           * ==================================================
           * SELECTED STATE OUTLINE
           * ==================================================
           */

          map.addLayer({

            id:
              "selected-state-outline",

            type:
              "line",

            source:
              "india-states",

            filter: [
              "==",
              [
                "get",
                "shapeName",
              ],
              "__NO_STATE__",
            ],

            paint: {

              "line-color":
                "#00ffff",

              "line-width":
                6,

              "line-opacity":
                1,

            },

          });


          /*
           * ==================================================
           * RAINFALL SOURCE
           * ==================================================
           */

          map.addSource(
            "imd-rainfall",
            {
              type:
                "geojson",

              data: {
                type:
                  "FeatureCollection",

                features: [],
              },
            }
          );


          /*
           * ==================================================
           * RAINFALL CIRCLES
           * ==================================================
           */

          map.addLayer({

            id:
              "imd-rainfall-circles",

            type:
              "circle",

            source:
              "imd-rainfall",

            minzoom:
              3,

            paint: {

              /*
               * Circle size changes according
               * to rainfall intensity.
               */

              "circle-radius": [

                "interpolate",

                [
                  "linear"
                ],

                [
                  "get",
                  "rainfall_mm"
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


              /*
               * Rainfall color scale.
               */

              "circle-color": [

                "interpolate",

                [
                  "linear"
                ],

                [
                  "get",
                  "rainfall_mm"
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


              "circle-opacity":
                0.72,

              "circle-stroke-color":
                "#ffffff",

              "circle-stroke-width":
                0.5,

              "circle-stroke-opacity":
                0.35,

            },

          });


          /*
           * ==================================================
           * LOAD REAL IMD RAINFALL
           * ==================================================
           */

          console.log(
            "Loading IMD rainfall:",
            rainfallDate
          );


          try {

            const rainfallResponse =
              await fetch(
                `/api/rainfall/grid/${rainfallDate}`,
                {
                  cache:
                    "no-store",
                }
              );


            if (
              !rainfallResponse.ok
            ) {

              throw new Error(
                `Rainfall API returned HTTP ${rainfallResponse.status}`
              );

            }


            const rainfallGeoJson =
              (await rainfallResponse.json()) as RainfallGeoJSON;


            /*
             * ==================================================
             * VALIDATE RAINFALL GEOJSON
             * ==================================================
             */

            if (
              !rainfallGeoJson ||
              rainfallGeoJson.type !==
                "FeatureCollection"
            ) {

              throw new Error(
                "Rainfall API returned invalid GeoJSON."
              );

            }


            console.log(
              "IMD rainfall loaded successfully."
            );


            console.log(
              "Rainfall features:",
              rainfallGeoJson.features.length
            );


            /*
             * ==================================================
             * UPDATE MAP SOURCE
             * ==================================================
             */

            const rainfallSource =
              map.getSource(
                "imd-rainfall"
              ) as
                | GeoJSONSource
                | undefined;


            if (
              rainfallSource
            ) {

              rainfallSource.setData(
                rainfallGeoJson as any
              );

            }


            setIsRainfallLoaded(
              true
            );


          } catch (
            rainfallLoadingError
          ) {

            console.error(
              "Rainfall loading error:",
              rainfallLoadingError
            );


            const rainfallMessage =
              rainfallLoadingError instanceof
              Error
                ? rainfallLoadingError.message
                : "Failed to load IMD rainfall data.";


            setRainfallError(
              rainfallMessage
            );

          }


          /*
           * ==================================================
           * MAP READY
           * ==================================================
           */

          setIsLoaded(
            true
          );


          console.log(
            "India state boundaries loaded successfully."
          );


          console.log(
            "IMD rainfall layer ready."
          );


          /*
           * ==================================================
           * STATE HOVER
           * ==================================================
           */

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


          /*
           * ==================================================
           * STATE CLICK
           * ==================================================
           */

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


              /*
               * =================================================
               * TURF POINT
               * =================================================
               */

              const clickPoint =
                turf.point([
                  event.lngLat.lng,
                  event.lngLat.lat,
                ]);


              /*
               * =================================================
               * FIND STATE
               * =================================================
               */

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
                  feature.geometry.type;


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


              /*
               * =================================================
               * NO STATE
               * =================================================
               */

              if (
                !foundFeature
              ) {

                console.log(
                  "No India state at this click."
                );

                return;

              }


              /*
               * =================================================
               * STATE NAME
               * =================================================
               */

              const stateName =
                getFeatureName(
                  foundFeature.properties
                );


              console.log(
                "Clicked state properties:",
                foundFeature.properties
              );


              console.log(
                "SELECTED STATE:",
                stateName
              );


              /*
               * =================================================
               * APPLY CYAN STATE SELECTION
               * =================================================
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

                    [
                      "get",
                      "shapeName",
                    ],

                    stateName,
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

                    [
                      "get",
                      "shapeName",
                    ],

                    stateName,
                  ]

                );

              }


              console.log(
                "STATE FILTER APPLIED:",
                stateName
              );


              /*
               * =================================================
               * SEND STATE TO PARENT
               * =================================================
               */

              if (
                onStateSelectRef.current
              ) {

                onStateSelectRef.current(
                  stateName
                );

              }


              /*
               * =================================================
               * ZOOM TO STATE
               * =================================================
               */

              try {

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
                      top:
                        80,

                      bottom:
                        80,

                      left:
                        80,

                      right:
                        80,
                    },

                    maxZoom:
                      7,

                    duration:
                      1000,

                    essential:
                      true,

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


          /*
           * ==================================================
           * RAINFALL HOVER
           * ==================================================
           */

          map.on(
            "mouseenter",

            "imd-rainfall-circles",

            () => {

              map
                .getCanvas()
                .style.cursor =
                "crosshair";

            }
          );


          map.on(
            "mouseleave",

            "imd-rainfall-circles",

            () => {

              map
                .getCanvas()
                .style.cursor =
                "";

            }
          );


          /*
           * ==================================================
           * RAINFALL CLICK
           * ==================================================
           */

          map.on(
            "click",

            "imd-rainfall-circles",

            (event) => {

              if (
                !event.features ||
                event.features.length ===
                  0
              ) {

                return;

              }


              const feature =
                event.features[0];


              const properties =
                feature.properties as
                  | {
                      rainfall_mm?: number;

                      date?: string;
                    }
                  | undefined;


              if (!properties) {
                return;
              }


              const rainfall =
                Number(
                  properties.rainfall_mm
                );


              const date =
                properties.date ||
                rainfallDate;


              new Popup({

                closeButton:
                  true,

                closeOnClick:
                  true,

              })

                .setLngLat(
                  event.lngLat
                )

                .setHTML(

                  `
                  <div
                    style="
                      font-family:
                        Arial,
                        sans-serif;
                      min-width:
                        150px;
                    "
                  >

                    <div
                      style="
                        font-size:
                          11px;
                        font-weight:
                          700;
                        letter-spacing:
                          0.08em;
                        margin-bottom:
                          6px;
                      "
                    >
                      IMD RAINFALL
                    </div>

                    <div
                      style="
                        font-size:
                          20px;
                        font-weight:
                          700;
                        margin-bottom:
                          4px;
                      "
                    >
                      ${
                        Number.isFinite(
                          rainfall
                        )
                          ? rainfall.toFixed(
                              2
                            )
                          : "N/A"
                      }
                      mm
                    </div>

                    <div
                      style="
                        font-size:
                          11px;
                        opacity:
                          0.7;
                      "
                    >
                      ${
                        date
                      }
                    </div>

                  </div>
                  `
                )

                .addTo(
                  map
                );

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


          setError(
            message
          );

        }

      }
    );


    /*
     * ========================================================
     * MAP ERROR
     * ========================================================
     */

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


    /*
     * ========================================================
     * CLEANUP
     * ========================================================
     */

    return () => {

      console.log(
        "Cleaning up MapView..."
      );


      if (
        mapRef.current
      ) {

        mapRef.current.remove();

        mapRef.current =
          null;

      }


      geoJsonDataRef.current =
        null;

    };

  }, []);


  /*
   * ==========================================================
   * UI
   * ==========================================================
   */

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

      {/* ====================================================
          MAP
          ==================================================== */}

      <div
        ref={
          mapContainerRef
        }

        style={{
          width:
            "100%",

          height:
            "100%",
        }}
      />


      {/* ====================================================
          MAP LOADING
          ==================================================== */}

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


      {/* ====================================================
          IMD STATUS
          ==================================================== */}

      {isLoaded && (

        <div
          style={{
            position:
              "absolute",

            top:
              "14px",

            left:
              "14px",

            zIndex:
              5,

            padding:
              "8px 12px",

            borderRadius:
              "6px",

            background:
              "rgba(0, 0, 0, 0.72)",

            color:
              "#ffffff",

            fontSize:
              "11px",

            fontWeight:
              600,

            letterSpacing:
              "0.05em",

            backdropFilter:
              "blur(6px)",
          }}
        >

          IMD RAINFALL

          <div
            style={{
              marginTop:
                "3px",

              fontSize:
                "10px",

              fontWeight:
                400,

              opacity:
                0.75,
            }}
          >

            {rainfallDate}

            {" • "}

            {isRainfallLoaded
              ? "DATA LOADED"
              : rainfallError
                ? "ERROR"
                : "LOADING"}

          </div>

        </div>

      )}


      {/* ====================================================
          RAINFALL LEGEND
          ==================================================== */}

      {isRainfallLoaded && (

        <div
          style={{
            position:
              "absolute",

            right:
              "14px",

            bottom:
              "50px",

            zIndex:
              5,

            width:
              "190px",

            padding:
              "12px",

            borderRadius:
              "7px",

            background:
              "rgba(0, 0, 0, 0.78)",

            color:
              "#ffffff",

            backdropFilter:
              "blur(6px)",

            fontSize:
              "10px",
          }}
        >

          <div
            style={{
              fontWeight:
                700,

              letterSpacing:
                "0.08em",

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
                "4px",

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

            <span>
              0 mm
            </span>

            <span>
              25
            </span>

            <span>
              50
            </span>

            <span>
              100
            </span>

            <span>
              200+
            </span>

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
              "14px",

            zIndex:
              8,

            maxWidth:
              "320px",

            padding:
              "10px 12px",

            borderRadius:
              "6px",

            background:
              "rgba(127, 29, 29, 0.92)",

            color:
              "#ffffff",

            fontSize:
              "11px",
          }}
        >

          IMD rainfall unavailable:
          {" "}
          {rainfallError}

        </div>

      )}


      {/* ====================================================
          GENERAL ERROR
          ==================================================== */}

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