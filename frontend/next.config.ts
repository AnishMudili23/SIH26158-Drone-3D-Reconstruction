import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: [
    "*.trycloudflare.com",
    "farming-coaches-carnival-vacancies.trycloudflare.com",
    "*.ngrok-free.app",
    "localhost:3000",
    "127.0.0.1:3000",
  ],
  async rewrites() {
    const backendUrl = process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
      {
        source: "/static/:path*",
        destination: `${backendUrl}/static/:path*`,
      },
      {
        source: "/viewer/:path*",
        destination: `${backendUrl}/viewer/:path*`,
      },
    ];
  },
};

export default nextConfig;
