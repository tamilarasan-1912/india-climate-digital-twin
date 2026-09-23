import type { NextConfig } from "next";
import { resolveDevOrigins } from "./scripts/dev-origins.mjs";

// Render-hosted FastAPI backend. NEXT_PUBLIC_API_URL can override this in Vercel.
const API = (process.env.NEXT_PUBLIC_API_URL || "https://india-climate-digital-twin-api.onrender.com").replace(/\/$/, "");

// Development-only hostname allowlist covering localhost and private-range LAN
// IPs, so the HMR WebSocket upgrades instead of being refused. No effect on
// builds or on the Vercel/Render deployments. See scripts/dev-origins.mjs.
const allowedDevOrigins = resolveDevOrigins();

// Every backend API group must be reachable through the frontend origin so the
// browser never needs a cross-origin request and CORS stays tight.
const API_PREFIXES = [
  "rainfall",
  "climate",
  "india",
  "v1",
  "gods-eye",
  "extreme-events",
  "risk",
  "twin",
  "historical",
  "forecast",
  "models",
  "ai",
  "explain",
  "scenarios",
  "system",
];

const nextConfig: NextConfig = {
  allowedDevOrigins,
  async rewrites() {
    return [
      ...API_PREFIXES.map(prefix => ({
        source: `/api/${prefix}/:path*`,
        destination: `${API}/api/${prefix}/:path*`,
      })),
      ...API_PREFIXES.map(prefix => ({
        source: `/api/${prefix}`,
        destination: `${API}/api/${prefix}`,
      })),
      { source: "/api/validation", destination: `${API}/api/validation` },
      { source: "/api/provenance", destination: `${API}/api/provenance` },
      { source: "/api/health", destination: `${API}/api/health` },
      { source: "/api/status", destination: `${API}/api/status` },
      { source: "/api/ready", destination: `${API}/api/ready` },
      { source: "/ogc/:path*", destination: `${API}/ogc/:path*` },
    ];
  },
};

export default nextConfig;