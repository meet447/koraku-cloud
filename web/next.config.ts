import type { NextConfig } from "next";

const backend = process.env.KORAKU_BACKEND_URL ?? "http://127.0.0.1:8000";
const isProd = process.env.NODE_ENV === "production";

const securityHeaders = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=()",
  },
  ...(isProd
    ? [
        {
          key: "Strict-Transport-Security",
          value: "max-age=63072000; includeSubDomains; preload",
        },
        {
          key: "Content-Security-Policy",
          value: [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: blob: https:",
            "font-src 'self' data:",
            "connect-src 'self' https: wss:",
            "frame-src 'self' blob:",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
          ].join("; "),
        },
      ]
    : []),
];

const nextConfig: NextConfig = {
  output: "standalone",
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: securityHeaders,
      },
    ];
  },
  async redirects() {
    return [
      { source: "/automations", destination: "/app/automations", permanent: false },
      { source: "/connections", destination: "/app/connections", permanent: false },
      { source: "/personalization", destination: "/app/settings", permanent: false },
      { source: "/skills", destination: "/app/connections", permanent: false },
      { source: "/app/skills", destination: "/app/connections", permanent: false },
    ];
  },
  async rewrites() {
    return [
      // /koraku-api/stream is handled by src/app/koraku-api/stream/route.ts (true streaming).
      { source: "/koraku-api/health", destination: `${backend}/health` },
      // /koraku-api/api/chat-models → Route Handler (session Bearer required)
      // /koraku-api/api/personalization → Route Handler (forwards Supabase Bearer from cookies)
      // /koraku-api/api/composio/* is handled by src/app/koraku-api/api/composio/[[...path]]/route.ts
      // so Authorization (Supabase Bearer token) is forwarded to Python.
      // /koraku-api/api/workspace/* is handled by src/app/koraku-api/api/workspace/[[...path]]/route.ts
      // /koraku-api/api/automations/* is handled by src/app/koraku-api/api/automations/[[...path]]/route.ts
      // so long-running POST …/run is not buffered or timed out by rewrites.
    ];
  },
};

export default nextConfig;
