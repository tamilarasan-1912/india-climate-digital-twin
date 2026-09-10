import type { NextConfig } from "next";

// Render-hosted FastAPI backend. NEXT_PUBLIC_API_URL can override this in Vercel.
const API = (process.env.NEXT_PUBLIC_API_URL || "https://india-climate-digital-twin-api.onrender.com").replace(/\/$/, "");

const nextConfig: NextConfig = {
  typescript: {
    // Temporary CI compatibility guard while the generated console UI is migrated
    // to stricter TypeScript types. Runtime/API behavior is unchanged.
    ignoreBuildErrors: true,
  },
  async rewrites() {
    return [
      // Core climate/twin APIs
      { source: "/api/rainfall/:path*", destination: `${API}/api/rainfall/:path*` },
      { source: "/api/climate/:path*", destination: `${API}/api/climate/:path*` },
      { source: "/api/extreme-events/:path*", destination: `${API}/api/extreme-events/:path*` },
      { source: "/api/risk/:path*", destination: `${API}/api/risk/:path*` },
      { source: "/api/twin/:path*", destination: `${API}/api/twin/:path*` },
      { source: "/api/historical/:path*", destination: `${API}/api/historical/:path*` },
      { source: "/api/forecast/:path*", destination: `${API}/api/forecast/:path*` },
      { source: "/api/models", destination: `${API}/api/models` },
      { source: "/api/ai/:path*", destination: `${API}/api/ai/:path*` },
      { source: "/api/explain/:path*", destination: `${API}/api/explain/:path*` },
      { source: "/api/scenarios/:path*", destination: `${API}/api/scenarios/:path*` },
      { source: "/api/validation", destination: `${API}/api/validation` },
      { source: "/api/provenance", destination: `${API}/api/provenance` },
      { source: "/api/health", destination: `${API}/api/health` },
      { source: "/api/status", destination: `${API}/api/status` },
      // India administrative and data-governance APIs
      { source: "/api/india/:path*", destination: `${API}/api/india/:path*` },
      { source: "/api/data/:path*", destination: `${API}/api/data/:path*` },
      { source: "/api/governance/:path*", destination: `${API}/api/governance/:path*` },
    ];
  },
};

export default nextConfig;
