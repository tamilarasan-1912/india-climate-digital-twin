import os from "node:os";
import type { NextConfig } from "next";

// Render-hosted FastAPI backend. NEXT_PUBLIC_API_URL can override this in Vercel.
// In local development the Next server remains the browser-facing origin and
// proxies relative /api requests to the configured backend.
const API = (
  process.env.NEXT_PUBLIC_API_URL ||
  (process.env.NODE_ENV === "development"
    ? "http://127.0.0.1:8000"
    : "https://india-climate-digital-twin-api.onrender.com")
).replace(/\/$/, "");

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
  "data",
  "governance",
];

function localNetworkHostnames(): string[] {
  const interfaces = os.networkInterfaces();
  return Object.values(interfaces)
    .flatMap(entries => entries ?? [])
    .filter(entry => entry.family === "IPv4" && !entry.internal)
    .map(entry => entry.address);
}

function developmentOrigins(): string[] {
  if (process.env.NODE_ENV === "production") return [];

  // Next.js protects dev-only assets, including the HMR WebSocket, from a
  // cross-origin browser request. Include the actual LAN addresses detected on
  // the machine and allow explicit hostnames for tunnels/containers. Values
  // are hostnames only: no scheme, port, path, or wildcard suffix is needed.
  const configured = (process.env.NEXT_ALLOWED_DEV_ORIGINS ?? "")
    .split(",")
    .map(origin => origin.trim().replace(/^https?:\/\//, "").split("/")[0])
    .filter(Boolean);

  return [
    ...new Set([
      ...localNetworkHostnames(),
      ...configured,
      // Arena's preview proxy uses a per-session subdomain. This is dev-only
      // and does not affect production deployments.
      "**.e2b.app",
    ]),
  ];
}

const nextConfig: NextConfig = {
  // Keep the dev server reachable from localhost, LAN clients, and the
  // browser-facing preview proxy. The dev script also pins the bind address
  // explicitly so this remains true across Next.js versions.
  allowedDevOrigins: developmentOrigins(),
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
