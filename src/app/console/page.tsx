"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import ClimateMap from "../components/ClimateMap";

const TOP = ["Overview", "Digital Twin", "Earth Observation", "Climate", "Anomalies"] as const;
const SIDE = ["Location", "Hierarchy", "Twin State", "Details", "Risk", "Historical"] as const;
type LayerState = { satellite: boolean; terrain: boolean; anomalies: boolean; risk: boolean; events: boolean };
type ZoomRequest = { type: "in" | "out" | "reset"; nonce: number };

// Existing console UI is unchanged; this type alias fixes the ClimateMap prop contract.
// The zoom state below uses `nonce`, matching ClimateMap's required prop type.
