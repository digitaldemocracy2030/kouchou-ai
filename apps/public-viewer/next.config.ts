import type { NextConfig } from "next";
import path from "path";

const isStaticExport = process.env.NEXT_PUBLIC_OUTPUT_MODE === "export";
const BASE_PATH = process.env.NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH || "";
const DIST_DIR = process.env.STATIC_EXPORT_DIST_DIR || ".next";

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
};

export default nextConfig;
