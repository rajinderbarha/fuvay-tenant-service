/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  // Keep generated AI-agent instruction files out of the application workspace.
  agentRules: false,

  env: {
    // Expose API URL to the browser bundle.
    // Set NEXT_PUBLIC_API_URL at build time in CI/CD for each environment.
    // Falls back to localhost for local dev only.
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },

  // Guard: MOCK_MODE must never be enabled in production builds.
  // If NEXT_PUBLIC_USE_MOCK is accidentally set in prod, this will throw at build time.
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
