import type { NextConfig } from "next";

const isStaticExport = process.env.NEXT_PUBLIC_OUTPUT_MODE === "export";
const BASE_PATH = process.env.NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH || "";

// Get the site URL for CSP configuration
// Defaults to http://localhost:3000 for development
const getSiteUrl = (): string => {
  return process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
};

// Build CSP header allowing both localhost and public IP access
const buildCSPHeader = (): string => {
  const siteUrl = getSiteUrl();

  // Extract domain/IP from site URL for CSP directives
  let cspDomain = "localhost";
  try {
    const urlObj = new URL(siteUrl);
    cspDomain = urlObj.hostname;
  } catch {
    // Fallback to localhost if URL parsing fails
    cspDomain = "localhost";
  }

  // CSP directives that allow both localhost and the configured site domain
  // Also allows ws/wss for WebSocket connections (used by Next.js dev tools)
  const cspDirectives = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://www.googletagmanager.com https://www.google-analytics.com",
    `img-src 'self' data: https: http://${cspDomain} http://localhost`,
    `connect-src 'self' https: http://${cspDomain} http://localhost ws://${cspDomain} ws://localhost wss://${cspDomain} wss://localhost https://www.google-analytics.com`,
    "font-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com data:",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "frame-ancestors 'none'",
    "form-action 'self'",
  ];

  return cspDirectives.join("; ");
};

const nextConfig: NextConfig = {
  basePath: isStaticExport ? BASE_PATH : "",
  assetPrefix: isStaticExport ? BASE_PATH : "",
  output: isStaticExport ? "export" : undefined,
  trailingSlash: true,
  experimental: {
    optimizePackageImports: ["@chakra-ui/react"],
  },
  headers: async () => {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "Content-Security-Policy",
            value: buildCSPHeader(),
          },
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "X-XSS-Protection",
            value: "1; mode=block",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
