/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",

  env: {
    // Set NEXT_PUBLIC_API_URL at build time for each environment.
    // Falls back to localhost for local dev only.
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },

  // Guard: MOCK_MODE must never be enabled in production builds.
  ...(process.env.NODE_ENV === "production" && process.env.NEXT_PUBLIC_USE_MOCK === "true"
    ? (() => { throw new Error("NEXT_PUBLIC_USE_MOCK must not be set to 'true' in production builds."); })()
    : {}),

  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options",         value: "DENY" },
          { key: "Referrer-Policy",          value: "strict-origin-when-cross-origin" },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
