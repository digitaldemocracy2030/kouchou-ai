import type { NextConfig } from "next";

// Get the site URL and API URL for CSP configuration
const getSiteUrl = (): string => {
  return process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
};

const getApiUrl = (): string => {
  return process.env.NEXT_PUBLIC_API_BASEPATH || "http://localhost:8000";
};

// Build CSP header allowing both localhost and public IP access
const buildCSPHeader = (): string => {
  const siteUrl = getSiteUrl();
  const apiUrl = getApiUrl();

  // Extract domain/IP from URLs for CSP directives
  let siteDomain = "localhost";
  let apiDomain = "localhost";

  try {
    const siteUrlObj = new URL(siteUrl);
    siteDomain = siteUrlObj.hostname;
  } catch {
    siteDomain = "localhost";
  }

  try {
    const apiUrlObj = new URL(apiUrl);
    apiDomain = apiUrlObj.hostname;
  } catch {
    apiDomain = "localhost";
  }

  // CSP directives that allow both localhost and the configured domains
  // Also allows ws/wss for WebSocket connections
  const cspDirectives = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://www.googletagmanager.com https://www.google-analytics.com",
    `img-src 'self' data: https: http://${siteDomain} http://${apiDomain} http://localhost`,
    `connect-src 'self' https: http://${siteDomain} http://${apiDomain} http://localhost ws://${siteDomain} ws://${apiDomain} ws://localhost wss://${siteDomain} wss://${apiDomain} wss://localhost https://www.google-analytics.com`,
    "font-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com data:",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "frame-ancestors 'none'",
    "form-action 'self'",
  ];

  return cspDirectives.join("; ");
};

const nextConfig: NextConfig = {
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
