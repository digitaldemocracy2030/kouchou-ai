import path from "node:path";
import type { NextConfig } from "next";
import { buildCspHeaderValue } from "../shared/csp";

const isStaticExport = process.env.NEXT_PUBLIC_OUTPUT_MODE === "export";
const BASE_PATH = process.env.NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH || "";
const DIST_DIR = process.env.STATIC_EXPORT_DIST_DIR || ".next";
const enableGoogleAnalytics = Boolean(process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID);
const contentSecurityPolicy = buildCspHeaderValue({
  apiBasePath: process.env.API_BASEPATH,
  publicApiBasePath: process.env.NEXT_PUBLIC_API_BASEPATH,
  siteUrl: process.env.NEXT_PUBLIC_SITE_URL,
  enableGoogleAnalytics,
  // Plotly scattergl uses regl, which requires runtime eval during WebGL initialization.
  allowUnsafeEval: true,
  isDevelopment: process.env.NODE_ENV !== "production",
});

const nextConfig: NextConfig = {
  basePath: isStaticExport ? BASE_PATH : "",
  assetPrefix: isStaticExport ? BASE_PATH : "",
  output: isStaticExport ? "export" : undefined,
  distDir: isStaticExport ? DIST_DIR : ".next",
  trailingSlash: true,
  turbopack: {
    // Ensure Turbopack resolves the monorepo workspace root correctly.
    root: path.join(__dirname, "../.."),
  },
  experimental: {
    optimizePackageImports: ["@chakra-ui/react"],
  },
  async rewrites() {
    if (isStaticExport) {
      return [];
    }

    // サーバーモードでは public/meta をコピーしないので、/meta/* の画像（favicon・作成者画像・OGP）は API へ転送する。
    // 静的書き出しでは copy-image が public/meta に画像を置く。
    const apiBasePath = (process.env.API_BASEPATH || process.env.NEXT_PUBLIC_API_BASEPATH || "").replace(/\/+$/, "");
    if (!apiBasePath) {
      return [];
    }

    return [
      {
        source: "/meta/:path*",
        destination: `${apiBasePath}/meta/:path*`,
      },
    ];
  },
  async headers() {
    if (isStaticExport) {
      return [];
    }

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
};

export default nextConfig;
