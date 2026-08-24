import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      // Rainfall
      {
        source: "/api/rainfall/:path*",
        destination:
          "http://127.0.0.1:8000/api/rainfall/:path*",
      },

      // Climate variables
      {
        source: "/api/climate/:path*",
        destination:
          "http://127.0.0.1:8000/api/climate/:path*",
      },

      // Extreme events
      {
        source: "/api/extreme-events/:path*",
        destination:
          "http://127.0.0.1:8000/api/extreme-events/:path*",
      },

      // Climate risk
      {
        source: "/api/risk/:path*",
        destination:
          "http://127.0.0.1:8000/api/risk/:path*",
      },
    ];
  },
};

export default nextConfig;
