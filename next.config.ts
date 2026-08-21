import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/rainfall/:path*",

        destination:
          "http://127.0.0.1:8000/api/rainfall/:path*",
      },
    ];
  },
};

export default nextConfig;