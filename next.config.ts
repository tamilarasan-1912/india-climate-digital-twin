import type { NextConfig } from "next";

const API = "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      { source: "/api/rainfall/:path*", destination: `${API}/api/rainfall/:path*` },
      { source: "/api/climate/:path*", destination: `${API}/api/climate/:path*` },
      { source: "/api/extreme-events/:path*", destination: `${API}/api/extreme-events/:path*` },
      { source: "/api/risk/:path*", destination: `${API}/api/risk/:path*` },
      { source: "/api/twin/:path*", destination: `${API}/api/twin/:path*` },
      { source: "/api/historical/:path*", destination: `${API}/api/historical/:path*` },
      { source: "/api/forecast/:path*", destination: `${API}/api/forecast/:path*` },
      { source: "/api/models", destination: `${API}/api/models` },
      { source: "/api/explain/:path*", destination: `${API}/api/explain/:path*` },
      { source: "/api/scenarios/:path*", destination: `${API}/api/scenarios/:path*` },
      { source: "/api/validation", destination: `${API}/api/validation` },
      { source: "/api/provenance", destination: `${API}/api/provenance` },
      { source: "/api/health", destination: `${API}/api/health` },
      { source: "/api/status", destination: `${API}/api/status` },
    ];
  },
};

export default nextConfig;
