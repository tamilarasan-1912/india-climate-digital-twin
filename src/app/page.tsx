"use client";

import { useState } from "react";
import MapView from "./components/MapView";

const layers = [
  "Temperature",
  "Rainfall",
  "Wind",
  "Humidity",
  "Land Surface Temperature",
];

const bottomTabs = [
  "Forecast",
  "Extreme Events",
  "Scenarios",
  "Models",
  "Validation",
];

export default function Home() {
  const [activeLayer, setActiveLayer] =
    useState("Temperature");

  const [activeTab, setActiveTab] =
    useState("Forecast");

  const [selectedState, setSelectedState] =
    useState("INDIA");

  return (
    <main className="app-shell">

      {/* TOP BAR */}
      <header className="topbar">
        <div>
          <div className="brand">
            <span className="brand-icon">🇮🇳</span>
            INDIA CLIMATE DIGITAL TWIN
          </div>

          <div className="subtitle">
            AI • EARTH OBSERVATION • CLIMATE INTELLIGENCE
          </div>
        </div>

        <div className="system-status">
          <span className="status-dot"></span>
          SYSTEM ONLINE
        </div>
      </header>


      {/* MAIN CONTENT */}
      <section className="workspace">

        {/* LEFT PANEL */}
        <aside className="left-panel">

          <div className="panel-title">
            LAYERS
          </div>

          <div className="layer-list">
            {layers.map((layer) => (
              <button
                key={layer}
                className={`layer-item ${
                  activeLayer === layer ? "active" : ""
                }`}
                onClick={() => setActiveLayer(layer)}
              >
                <span className="layer-indicator">
                  {activeLayer === layer ? "●" : "○"}
                </span>

                <span>{layer}</span>
              </button>
            ))}
          </div>


          <div className="panel-divider"></div>


          <div className="panel-title">
            MAP MODE
          </div>

          <button className="mode-button active-mode">
            2D MAP
          </button>

          <button className="mode-button">
            3D GLOBE
          </button>

        </aside>


        {/* MAP */}
        <section className="map-container">

          <div className="map-header">

            <span>
              {selectedState.toUpperCase()}
            </span>

            <span className="map-layer-label">
              ACTIVE LAYER: {activeLayer.toUpperCase()}
            </span>

          </div>


          <div className="map-area">

            <MapView
              onStateSelect={(stateName) =>
                setSelectedState(stateName)
              }
            />

            <div className="map-scale">
              0 ───────── 500 km
            </div>

          </div>

        </section>


        {/* RIGHT PANEL */}
        <aside className="right-panel">

          <div className="panel-title">
            CLIMATE STATE
          </div>


          {/* SELECTED STATE */}
          <div className="state-location">
            {selectedState.toUpperCase()} • SELECTED REGION
          </div>


          {/* TEMPERATURE */}
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


          {/* RAINFALL */}
          <div className="metric-card">

            <div className="metric-label">
              RAINFALL
            </div>

            <div className="metric-value">
              12.4 mm
            </div>

            <div className="metric-description">
              Demonstration value
            </div>

          </div>


          {/* HUMIDITY */}
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


          <div className="panel-divider"></div>


          {/* DATA SOURCE */}
          <div className="panel-title">
            DATA SOURCE
          </div>

          <div className="data-source">
            <span>●</span>
            Demonstration Data
          </div>

          <div className="source-warning">
            Live scientific datasets will be connected
            in later phases.
          </div>

        </aside>

      </section>


      {/* TIMELINE */}
      <section className="timeline-panel">

        <div className="timeline-header">

          <span>
            TIME
          </span>

          <span>
            20 AUG 2026 • 21:00 IST
          </span>

        </div>


        <div className="timeline">

          <div className="timeline-line"></div>

          <div className="timeline-point active-point"></div>

          <div className="timeline-labels">

            <span>2020</span>
            <span>2022</span>
            <span>2024</span>
            <span>2026</span>
            <span>2030</span>

          </div>

        </div>

      </section>


      {/* BOTTOM TABS */}
      <nav className="bottom-tabs">

        {bottomTabs.map((tab) => (

          <button
            key={tab}
            className={
              activeTab === tab
                ? "tab active-tab"
                : "tab"
            }
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>

        ))}

      </nav>


      {/* FOOTER */}
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