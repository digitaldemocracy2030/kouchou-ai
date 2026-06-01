import path from "node:path";
import type { NextConfig } from "next";
import { buildCspHeaderValue } from "../shared/csp";

// Standalone (Windows embeddable) build: static export served by FastAPI under a
// sub-path. Hosted deployment keeps output:"standalone" + Server Actions unchanged.
// The standalone build also runs scripts/standalone-prep.mjs to swap server-only
// pieces (Server Actions, root page SSR, route handlers, middleware) at build time.
const isStaticExport = process.env.NEXT_PUBLIC_OUTPUT_MODE === "export";
const BASE_PATH = process.env.NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH || "";

const enableGoogleAnalytics = Boolean(process.env.NEXT_PUBLIC_ADMIN_GA_MEASUREMENT_ID);
const contentSecurityPolicy = buildCspHeaderValue({
  apiBasePath: process.env.API_BASEPATH,
  publicApiBasePath: process.env.NEXT_PUBLIC_API_BASEPATH,
  siteUrl: process.env.NEXT_PUBLIC_SITE_URL,
  enableGoogleAnalytics,
  isDevelopment: process.env.NODE_ENV !== "production",
});

const nextConfig: NextConfig = {
  output: isStaticExport ? "export" : "standalone",
  basePath: isStaticExport ? BASE_PATH : "",
  assetPrefix: isStaticExport ? BASE_PATH : "",
  trailingSlash: isStaticExport ? true : undefined,
  outputFileTracingRoot: path.join(__dirname, "../../"),
  experimental: {
    optimizePackageImports: ["@chakra-ui/react"],
    serverActions: {
      bodySizeLimit: "100mb",
    },
  },
  serverExternalPackages: ["fs", "path"],
  // headers() is not applied with output:"export"; keep it only for the hosted build.
  ...(isStaticExport
    ? {}
    : {
        async headers() {
          return [
            {
              source: "/:path*",
              headers: [
                {
                  key: "Content-Security-Policy",
                  value: contentSecurityPolicy,
                },
              ],
            },
          ];
        },
      }),
};

export default nextConfig;
