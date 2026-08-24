"use client";

import { useEffect, useState } from "react";
import MapView from "./components/MapView";


/*
 * ============================================================
 * TYPES
 * ============================================================
 */

interface ClimateVariable {
  name: string;
  short_name: string;
  unit: string;
  description: string;
  provider: string;
  dataset: string | null;
  variable: string | null;
  status: "active" | "planned";
  endpoint: string;
}

interface ClimateVariablesResponse {
  variables: Record<
    string,
    ClimateVariable
  >;
}

interface ExtremeEventSummary {
  total_extreme_points: number;
  heavy_points: number;
  very_heavy_points: number;
  extremely_heavy_points: number;
  maximum_rainfall_mm: number | null;
  maximum_location: {
    latitude: number;
    longitude: number;
  } | null;
}

interface ExtremeEventResponse {
  date: string;
  variable: string;
  units: string;
  thresholds: {
    heavy_mm: number;
    very_heavy_mm: number;
    extremely_heavy_mm: number;
  };
  summary: ExtremeEventSummary;
}

interface ClimateRiskSummary {
  date: string;
  variable: string;
  units: string;
  risk_model: string;

  score_range: {
    minimum: number;
    maximum: number;
  };

  thresholds: {
    heavy_mm: number;
    very_heavy_mm: number;
    extremely_heavy_mm: number;
  };

  grid: {
    latitude_count: number;
    longitude_count: number;
    total_points: number;
    valid_points: number;
  };

  risk_distribution: {
    low: number;
    moderate: number;
    high: number;
    extreme: number;
    no_data: number;
  };

  statistics: {
    mean_hazard_score: number | null;
    maximum_hazard_score: number | null;
  };

  maximum_risk: {
    latitude: number;
    longitude: number;
    rainfall_mm: number;
    hazard_score: number;
    risk_category: string;
    rainfall_category: string;
  } | null;
}


/*
 * ============================================================
 * BOTTOM TABS
 * ============================================================
 */

const bottomTabs = [
  "Forecast",
  "Extreme Events",
  "Scenarios",
  "Models",
  "Validation",
];


/*
 * ============================================================
 * API URL
 * ============================================================
 *
 * The Next.js rewrite in next.config.ts forwards:
 *
 * /api/rainfall/*
 * /api/climate/*
 *
 * to FastAPI on port 8000.
 *
 * Therefore the browser can safely use:
 *
 * /api/climate/variables
 *
 * ============================================================
 */


/*
 * ============================================================
 * HOME
 * ============================================================
 */

export default function Home() {

  /*
   * ==========================================================
   * CLIMATE VARIABLES
   * ==========================================================
   */

  const [
    climateVariables,
    setClimateVariables,
  ] = useState<
    Record<
      string,
      ClimateVariable
    >
  >({});


  /*
   * ==========================================================
   * ACTIVE LAYER
   * ==========================================================
   */

  const [
    activeLayer,
    setActiveLayer,
  ] = useState("Rainfall");


  /*
   * ==========================================================
   * ACTIVE TAB
   * ==========================================================
   */

  const [
    activeTab,
    setActiveTab,
  ] = useState("Forecast");


  /*
   * ==========================================================
   * SELECTED STATE
   * ==========================================================
   */

  const [
    selectedState,
    setSelectedState,
  ] = useState("INDIA");


  /*
   * ==========================================================
   * LOADING STATE
   * ==========================================================
   */

  const [
    layersLoading,
    setLayersLoading,
  ] = useState(true);


  /*
   * ==========================================================
   * API ERROR
   * ==========================================================
   */

  const [
    layersError,
    setLayersError,
  ] = useState<string | null>(null);


  /*
   * ==========================================================
   * EXTREME EVENTS
   * ==========================================================
   */

  const [
    extremeEvents,
    setExtremeEvents,
  ] = useState<ExtremeEventResponse | null>(
    null
  );

  const [
    extremeEventsLoading,
    setExtremeEventsLoading,
  ] = useState(false);

  const [
    extremeEventsError,
    setExtremeEventsError,
  ] = useState<string | null>(null);

  const EXTREME_EVENTS_DATE =
    "2024-07-15";

  const [
    climateRisk,
    setClimateRisk,
  ] = useState<ClimateRiskSummary | null>(
    null
  );

  const [
    climateRiskLoading,
    setClimateRiskLoading,
  ] = useState(false);

  const [
    climateRiskError,
    setClimateRiskError,
  ] = useState<string | null>(null);

  const CLIMATE_RISK_DATE =
    "2024-07-15";


  /*
   * ==========================================================
   * LOAD CLIMATE VARIABLES
   * ==========================================================
   */

  useEffect(() => {

    let cancelled = false;


    async function loadClimateVariables() {

      try {

        setLayersLoading(
          true
        );

        setLayersError(
          null
        );


        console.log(
          "Loading climate variables..."
        );


        const response =
          await fetch(
            "/api/climate/variables",
            {
              cache:
                "no-store",
            }
          );


        if (
          !response.ok
        ) {

          throw new Error(
            `Climate variables API returned HTTP ${response.status}`
          );

        }


        const data =
          (await response.json()) as
            ClimateVariablesResponse;


        if (
          !data ||
          !data.variables
        ) {

          throw new Error(
            "Climate variables API returned invalid data."
          );

        }


        if (
          cancelled
        ) {
          return;
        }


        setClimateVariables(
          data.variables
        );


        /*
         * Make sure Rainfall remains the
         * default active scientific layer.
         */

        if (
          data.variables.rainfall
        ) {

          setActiveLayer(
            data.variables.rainfall.name
          );

        }


        console.log(
          "Climate variables loaded:",
          data.variables
        );


      } catch (error) {

        console.error(
          "Failed to load climate variables:",
          error
        );


        if (
          !cancelled
        ) {

          setLayersError(
            error instanceof Error
              ? error.message
              : "Failed to load climate variables."
          );

        }

      } finally {

        if (
          !cancelled
        ) {

          setLayersLoading(
            false
          );

        }

      }

    }


    loadClimateVariables();


    return () => {

      cancelled =
        true;

    };

  }, []);


  /*
   * ==========================================================
   * LOAD EXTREME EVENTS
   * ==========================================================
   */

  useEffect(() => {

    let cancelled = false;


    async function loadExtremeEvents() {

      try {

        setExtremeEventsLoading(
          true
        );

        setExtremeEventsError(
          null
        );

        const response =
          await fetch(
            `/api/extreme-events/summary/${EXTREME_EVENTS_DATE}`,
            {
              cache: "no-store",
            }
          );

        if (!response.ok) {
          throw new Error(
            `Extreme events API returned HTTP ${response.status}`
          );
        }

        const data =
          (await response.json()) as
            ExtremeEventResponse;

        if (
          !data ||
          !data.summary
        ) {
          throw new Error(
            "Extreme events API returned invalid data."
          );
        }

        if (cancelled) {
          return;
        }

        setExtremeEvents(
          data
        );

      } catch (error) {

        console.error(
          "Failed to load extreme events:",
          error
        );

        if (!cancelled) {

          setExtremeEventsError(
            error instanceof Error
              ? error.message
              : "Failed to load extreme events."
          );

        }

      } finally {

        if (!cancelled) {

          setExtremeEventsLoading(
            false
          );

        }

      }

    }


    loadExtremeEvents();


    return () => {

      cancelled = true;

    };

  }, []);


  /*
   * ==========================================================
   * LOAD CLIMATE RISK
   * ==========================================================
   */

  useEffect(() => {

    let cancelled = false;

    async function loadClimateRisk() {

      try {

        setClimateRiskLoading(
          true
        );

        setClimateRiskError(
          null
        );

        console.log(
          "Loading climate risk summary..."
        );

        const response =
          await fetch(
            `/api/risk/summary/${CLIMATE_RISK_DATE}`,
            {
              cache: "no-store",
            }
          );

        if (!response.ok) {

          throw new Error(
            `Climate risk API returned HTTP ${response.status}`
          );

        }

        const data =
          (await response.json()) as
            ClimateRiskSummary;

        if (
          !data ||
          !data.risk_distribution ||
          !data.statistics
        ) {

          throw new Error(
            "Climate risk API returned invalid data."
          );

        }

        if (cancelled) {
          return;
        }

        setClimateRisk(
          data
        );

        console.log(
          "Climate risk loaded:",
          data
        );

      } catch (error) {

        console.error(
          "Failed to load climate risk:",
          error
        );

        if (!cancelled) {

          setClimateRiskError(
            error instanceof Error
              ? error.message
              : "Failed to load climate risk."
          );

        }

      } finally {

        if (!cancelled) {

          setClimateRiskLoading(
            false
          );

        }

      }

    }

    loadClimateRisk();

    return () => {

      cancelled = true;

    };

  }, []);


  /*
   * ==========================================================
   * CONVERT API OBJECT INTO ARRAY
   * ==========================================================
   */

  const layers =
    Object.entries(
      climateVariables
    );


  /*
   * ==========================================================
   * HANDLE LAYER SELECTION
   * ==========================================================
   */

  const handleLayerSelect = (
    variableKey: string,
    variable: ClimateVariable
  ) => {

    console.log(
      "Selected climate layer:",
      variableKey
    );

    console.log(
      "Climate variable:",
      variable
    );


    /*
     * Only active scientific datasets should
     * currently be treated as available.
     *
     * Rainfall is active.
     *
     * Temperature/Wind/Humidity/LST are planned.
     */

    if (
      variable.status !==
      "active"
    ) {

      console.log(
        `${variable.name} is currently planned and has no connected dataset yet.`
      );

      return;

    }


    setActiveLayer(
      variable.name
    );

  };


  /*
   * ==========================================================
   * FIND ACTIVE VARIABLE
   * ==========================================================
   */

  const activeVariable =
    layers.find(
      ([, variable]) =>
        variable.name ===
        activeLayer
    );


  /*
   * ==========================================================
   * RENDER
   * ==========================================================
   */

  return (

    <main className="app-shell">

      {/* ====================================================
          TOP BAR
          ==================================================== */}

      <header className="topbar">

        <div>

          <div className="brand">

            <span className="brand-icon">
              🇮🇳
            </span>

            INDIA CLIMATE DIGITAL TWIN

          </div>


          <div className="subtitle">

            AI • EARTH OBSERVATION •
            CLIMATE INTELLIGENCE

          </div>

        </div>


        <div className="system-status">

          <span className="status-dot"></span>

          SYSTEM ONLINE

        </div>

      </header>


      {/* ====================================================
          MAIN CONTENT
          ==================================================== */}

      <section className="workspace">


        {/* ==================================================
            LEFT PANEL
            ================================================== */}

        <aside className="left-panel">

          <div className="panel-title">
            LAYERS
          </div>


          {/* =================================================
              LOADING
              ================================================= */}

          {layersLoading && (

            <div
              style={{
                padding:
                  "10px 0",

                fontSize:
                  "12px",

                opacity:
                  0.7,
              }}
            >
              Loading climate layers...
            </div>

          )}


          {/* =================================================
              ERROR
              ================================================= */}

          {layersError && (

            <div
              style={{
                padding:
                  "10px",

                marginBottom:
                  "10px",

                borderRadius:
                  "6px",

                background:
                  "rgba(127, 29, 29, 0.15)",

                fontSize:
                  "11px",
              }}
            >
              Climate API error:
              {" "}
              {layersError}
            </div>

          )}


          {/* =================================================
              LAYER LIST
              ================================================= */}

          {!layersLoading && (

            <div className="layer-list">

              {layers.map(
                ([
                  variableKey,
                  variable,
                ]) => {

                  const isActive =
                    activeLayer ===
                    variable.name;


                  const isAvailable =
                    variable.status ===
                    "active";


                  return (

                    <button

                      key={
                        variableKey
                      }

                      className={`layer-item ${
                        isActive
                          ? "active"
                          : ""
                      }`}

                      onClick={() =>
                        handleLayerSelect(
                          variableKey,
                          variable
                        )
                      }

                      title={
                        isAvailable
                          ? `${variable.name} — ${variable.provider}`
                          : `${variable.name} — dataset not connected yet`
                      }

                      style={{
                        opacity:
                          isAvailable
                            ? 1
                            : 0.55,

                        cursor:
                          isAvailable
                            ? "pointer"
                            : "not-allowed",
                      }}

                    >

                      <span className="layer-indicator">

                        {isActive
                          ? "●"
                          : "○"}

                      </span>


                      <span>

                        {
                          variable.name
                        }

                      </span>


                      {/* =====================================
                          STATUS
                          ===================================== */}

                      {!isAvailable && (

                        <span
                          style={{
                            marginLeft:
                              "auto",

                            fontSize:
                              "9px",

                            opacity:
                              0.6,

                            letterSpacing:
                              "0.04em",
                          }}
                        >
                          SOON
                        </span>

                      )}

                    </button>

                  );

                }
              )}

            </div>

          )}


          {/* =================================================
              DIVIDER
              ================================================= */}

          <div className="panel-divider"></div>


          {/* =================================================
              MAP MODE
              ================================================= */}

          <div className="panel-title">
            MAP MODE
          </div>


          <button
            className="mode-button active-mode"
          >
            2D MAP
          </button>


          <button
            className="mode-button"
            disabled
            title="3D Globe will be implemented in a later step."
            style={{
              opacity:
                0.55,

              cursor:
                "not-allowed",
            }}
          >
            3D GLOBE
          </button>

        </aside>


        {/* ==================================================
            MAP
            ================================================== */}

        <section className="map-container">


          {/* =================================================
              MAP HEADER
              ================================================= */}

          <div className="map-header">

            <span>
              {
                selectedState.toUpperCase()
              }
            </span>


            <span className="map-layer-label">

              ACTIVE LAYER:

              {" "}

              {
                activeLayer.toUpperCase()
              }

            </span>

          </div>


          {/* =================================================
              MAP AREA
              ================================================= */}

          <div className="map-area">

            <MapView

              onStateSelect={(
                stateName
              ) =>
                setSelectedState(
                  stateName
                )
              }

            />


            <div className="map-scale">

              0 ───────── 500 km

            </div>

          </div>

        </section>


        {activeTab === "Extreme Events" && (

          <section
            style={{
              padding: "14px 18px",
              borderTop:
                "1px solid rgba(255,255,255,0.08)",
              background:
                "rgba(5, 15, 30, 0.96)",
            }}
          >

            <div
              style={{
                fontSize: "12px",
                fontWeight: 800,
                letterSpacing: "0.08em",
                marginBottom: "12px",
              }}
            >
              EXTREME EVENTS &amp; CLIMATE RISK
            </div>

            {extremeEvents && (

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns:
                    "repeat(4, minmax(0, 1fr))",
                  gap: "8px",
                }}
              >

                <div className="metric-card">
                  <div className="metric-label">
                    EXTREME POINTS
                  </div>
                  <div className="metric-value">
                    {extremeEvents.summary.total_extreme_points}
                  </div>
                </div>

                <div className="metric-card">
                  <div className="metric-label">
                    HEAVY
                  </div>
                  <div className="metric-value">
                    {extremeEvents.summary.heavy_points}
                  </div>
                </div>

                <div className="metric-card">
                  <div className="metric-label">
                    VERY HEAVY
                  </div>
                  <div className="metric-value">
                    {extremeEvents.summary.very_heavy_points}
                  </div>
                </div>

                <div className="metric-card">
                  <div className="metric-label">
                    EXTREMELY HEAVY
                  </div>
                  <div className="metric-value">
                    {extremeEvents.summary.extremely_heavy_points}
                  </div>
                </div>

              </div>

            )}

            {climateRisk && (

              <div
                style={{
                  marginTop: "10px",
                  fontSize: "10px",
                  opacity: 0.8,
                }}
              >
                Rainfall Hazard Index v1 • {climateRisk.date} • {" "}
                {climateRisk.grid.valid_points.toLocaleString()} valid grid points
              </div>

            )}

          </section>

        )}


        {/* ==================================================
            RIGHT PANEL
            ================================================== */}

        <aside className="right-panel">


          {/* =================================================
              CLIMATE STATE
              ================================================= */}

          <div className="panel-title">

            CLIMATE STATE

          </div>


          {/* =================================================
              SELECTED STATE
              ================================================= */}

          <div className="state-location">

            {
              selectedState.toUpperCase()
            }

            {" • SELECTED REGION"}

          </div>


          {/* =================================================
              ACTIVE LAYER INFORMATION
              ================================================= */}

          {activeVariable && (

            <div
              style={{
                marginBottom:
                  "12px",

                fontSize:
                  "10px",

                opacity:
                  0.65,

                letterSpacing:
                  "0.04em",
              }}
            >

              SOURCE:

              {" "}

              {
                activeVariable[1]
                  .provider
              }

              {" • "}

              UNIT:

              {" "}

              {
                activeVariable[1]
                  .unit
              }

            </div>

          )}


          {/* =================================================
              TEMPERATURE
              ================================================= */}

          <div className="metric-card">

            <div className="metric-label">

              TEMPERATURE

            </div>


            <div className="metric-value">

              28.4°C

            </div>


            <div className="metric-description">

              Demonstration value

            </div>

          </div>


          {/* =================================================
              RAINFALL
              ================================================= */}

          <div className="metric-card">

            <div className="metric-label">

              RAINFALL

            </div>


            <div className="metric-value">

              12.4 mm

            </div>


            <div className="metric-description">

              IMD dataset connected

            </div>

          </div>


          {/* =================================================
              HUMIDITY
              ================================================= */}

          <div className="metric-card">

            <div className="metric-label">

              HUMIDITY

            </div>


            <div className="metric-value">

              71%

            </div>


            <div className="metric-description">

              Demonstration value

            </div>

          </div>


          {/* =====================================================
              CLIMATE RISK
              ===================================================== */}

          <div className="panel-divider"></div>

          <div className="panel-title">
            CLIMATE RISK
          </div>

          {climateRiskLoading && (

            <div
              style={{
                padding: "10px 0",
                fontSize: "11px",
                opacity: 0.7,
              }}
            >
              Loading risk analysis...
            </div>

          )}

          {climateRiskError && (

            <div
              style={{
                padding: "9px",
                marginBottom: "8px",
                borderRadius: "6px",
                background:
                  "rgba(127, 29, 29, 0.15)",
                fontSize: "10px",
              }}
            >
              Risk API error:
              {" "}
              {climateRiskError}
            </div>

          )}

          {climateRisk && (

            <>

              <div className="metric-card">

                <div className="metric-label">
                  VALID GRID POINTS
                </div>

                <div className="metric-value">
                  {climateRisk.grid.valid_points.toLocaleString()}
                </div>

                <div className="metric-description">
                  IMD rainfall observations
                </div>

              </div>

              <div className="metric-card">

                <div className="metric-label">
                  MAX HAZARD SCORE
                </div>

                <div className="metric-value">
                  {climateRisk.statistics.maximum_hazard_score !== null
                    ? climateRisk.statistics.maximum_hazard_score.toFixed(2)
                    : "-"}
                </div>

                <div className="metric-description">
                  Scale: 0-100
                </div>

              </div>

              <div
                style={{
                  marginTop: "8px",
                  fontSize: "10px",
                }}
              >

                <div
                  style={{
                    marginBottom: "7px",
                    fontWeight: 700,
                    letterSpacing: "0.06em",
                  }}
                >
                  RISK DISTRIBUTION
                </div>

                <div
                  style={{
                    display: "grid",
                    gap: "5px",
                  }}
                >

                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                    }}
                  >
                    <span>LOW</span>
                    <strong>
                      {climateRisk.risk_distribution.low.toLocaleString()}
                    </strong>
                  </div>

                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                    }}
                  >
                    <span>MODERATE</span>
                    <strong>
                      {climateRisk.risk_distribution.moderate.toLocaleString()}
                    </strong>
                  </div>

                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                    }}
                  >
                    <span>HIGH</span>
                    <strong>
                      {climateRisk.risk_distribution.high.toLocaleString()}
                    </strong>
                  </div>

                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                    }}
                  >
                    <span>EXTREME</span>
                    <strong>
                      {climateRisk.risk_distribution.extreme.toLocaleString()}
                    </strong>
                  </div>

                </div>

              </div>

              {climateRisk.maximum_risk && (

                <div
                  style={{
                    marginTop: "12px",
                    padding: "9px",
                    borderRadius: "6px",
                    background:
                      "rgba(127, 29, 29, 0.12)",
                    border:
                      "1px solid rgba(239, 68, 68, 0.25)",
                    fontSize: "10px",
                  }}
                >

                  <div
                    style={{
                      fontWeight: 800,
                      marginBottom: "6px",
                      letterSpacing: "0.05em",
                    }}
                  >
                    MAXIMUM RISK LOCATION
                  </div>

                  <div>
                    {climateRisk.maximum_risk.latitude.toFixed(2)}
                    deg N, {climateRisk.maximum_risk.longitude.toFixed(2)}
                    deg E
                  </div>

                  <div>
                    Rainfall:
                    {" "}
                    <strong>
                      {climateRisk.maximum_risk.rainfall_mm.toFixed(2)} mm
                    </strong>
                  </div>

                  <div>
                    Hazard:
                    {" "}
                    <strong>
                      {climateRisk.maximum_risk.hazard_score.toFixed(2)}
                    </strong>
                  </div>

                  <div>
                    Category:
                    {" "}
                    <strong>
                      {climateRisk.maximum_risk.risk_category.toUpperCase()}
                    </strong>
                  </div>

                </div>

              )}

            </>

          )}


          {/* =================================================
              DIVIDER
              ================================================= */}

          <div className="panel-divider"></div>


          {/* =================================================
              DATA SOURCE
              ================================================= */}

          <div className="panel-title">

            DATA SOURCE

          </div>


          <div className="data-source">

            <span>
              ●
            </span>

            {

              activeVariable
                ? activeVariable[1]
                    .provider
                : "Climate API"

            }

          </div>


          <div className="source-warning">

            {activeVariable &&
            activeVariable[1]
              .status === "active"

              ? `${activeVariable[1].name} is connected to the scientific backend.`

              : "Scientific dataset for this variable will be connected in a later phase."
            }

          </div>

        </aside>

      </section>


      {/* ====================================================
          TIMELINE
          ==================================================== */}

      <section className="timeline-panel">


        <div className="timeline-header">

          <span>
            TIME
          </span>


          <span>
            15 JUL 2024 • IMD DATA
          </span>

        </div>


        <div className="timeline">

          <div className="timeline-line"></div>


          <div className="timeline-point active-point"></div>


          <div className="timeline-labels">

            <span>
              2020
            </span>

            <span>
              2022
            </span>

            <span>
              2024
            </span>

            <span>
              2026
            </span>

            <span>
              2030
            </span>

          </div>

        </div>

      </section>


      {/* ====================================================
          EXTREME EVENTS
          ==================================================== */}

      <section
        style={{
          padding: "16px 22px",
          borderTop: "1px solid var(--border)",
          background: "rgba(11, 21, 31, 0.96)",
        }}
      >
        <div className="panel-title">
          EXTREME RAINFALL EVENTS
        </div>

        {extremeEventsLoading && (
          <div
            style={{
              fontSize: "12px",
              opacity: 0.6,
            }}
          >
            Loading extreme events...
          </div>
        )}

        {extremeEventsError && (
          <div
            style={{
              fontSize: "11px",
              color: "#fca5a5",
            }}
          >
            Extreme events unavailable: {extremeEventsError}
          </div>
        )}

        {extremeEvents && !extremeEventsLoading && (
          <>
            <div
              style={{
                display: "grid",
                gridTemplateColumns:
                  "repeat(auto-fit, minmax(130px, 1fr))",
                gap: "10px",
              }}
            >
              <div className="metric-card">
                <div className="metric-label">
                  TOTAL EXTREME POINTS
                </div>
                <div className="metric-value">
                  {extremeEvents.summary.total_extreme_points}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-label">
                  HEAVY
                </div>
                <div className="metric-value">
                  {extremeEvents.summary.heavy_points}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-label">
                  VERY HEAVY
                </div>
                <div className="metric-value">
                  {extremeEvents.summary.very_heavy_points}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-label">
                  EXTREMELY HEAVY
                </div>
                <div className="metric-value">
                  {extremeEvents.summary.extremely_heavy_points}
                </div>
              </div>
            </div>

            <div
              style={{
                marginTop: "12px",
                fontSize: "12px",
                fontWeight: 700,
              }}
            >
              Maximum rainfall: {" "}
              {extremeEvents.summary.maximum_rainfall_mm ?? "N/A"} mm
            </div>

            {extremeEvents.summary.maximum_location ? (
              <div
                style={{
                  marginTop: "8px",
                  fontSize: "11px",
                  opacity: 0.7,
                }}
              >
                Location: {" "}
                {extremeEvents.summary.maximum_location.latitude.toFixed(4)}, {" "}
                {extremeEvents.summary.maximum_location.longitude.toFixed(4)}
              </div>
            ) : (
              <div
                style={{
                  marginTop: "8px",
                  fontSize: "12px",
                  opacity: 0.6,
                }}
              >
                Location unavailable
              </div>
            )}

            {/* THRESHOLDS */}
            <div
              style={{
                marginTop: "12px",
                display: "flex",
                gap: "18px",
                flexWrap: "wrap",
                fontSize: "10px",
                opacity: 0.65,
              }}
            >
              <span>
                Heavy ≥ {extremeEvents.thresholds.heavy_mm} mm
              </span>
              <span>
                Very Heavy ≥ {extremeEvents.thresholds.very_heavy_mm} mm
              </span>
              <span>
                Extremely Heavy ≥ {" "}
                {extremeEvents.thresholds.extremely_heavy_mm} mm
              </span>
            </div>
          </>
        )}
      </section>


      {/* ====================================================
          BOTTOM TABS
          ==================================================== */}

      <nav className="bottom-tabs">

        {bottomTabs.map(
          (tab) => (

            <button

              key={
                tab
              }

              className={
                activeTab ===
                tab

                  ? "tab active-tab"

                  : "tab"
              }

              onClick={() =>
                setActiveTab(
                  tab
                )
              }

            >

              {tab}

            </button>

          )
        )}

      </nav>


      {/* ====================================================
          FOOTER
          ==================================================== */}

      <footer className="footer">

        <span>

          INDIA CLIMATE DIGITAL TWIN

        </span>


        <span>

          Prototype • Scientific Visualization Platform

        </span>

      </footer>

    </main>

  );
}