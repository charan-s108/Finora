/** @type {import('next').NextConfig} */
const nextConfig = {
  // Required for Railway Docker deployment (standalone output = single server.js)
  output: "standalone",

  images: {
    remotePatterns: [
      { protocol: "https", hostname: "logo.clearbit.com" },
    ],
  },

  async rewrites() {
    // BACKEND_URL = private server-side var (Vercel dashboard / Railway env)
    // NEXT_PUBLIC_BACKEND_URL = public fallback for local dev
    const backendUrl =
      process.env.BACKEND_URL ||
      process.env.NEXT_PUBLIC_BACKEND_URL ||
      "http://localhost:8000";
    return [
      {
        source: "/api/stocks/:path*",
        destination: `${backendUrl}/api/stocks/:path*`,
      },
      {
        source: "/api/health",
        destination: `${backendUrl}/api/health`,
      },
    ];
  },
};

export default nextConfig;
