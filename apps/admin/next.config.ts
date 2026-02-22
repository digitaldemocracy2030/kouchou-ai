import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    optimizePackageImports: ["@chakra-ui/react"],
    serverActions: {
      bodySizeLimit: "100mb",
    },
  },
  serverExternalPackages: ["fs", "path"],
};

export default nextConfig;
