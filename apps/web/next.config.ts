import path from "node:path";

import type { NextConfig } from "next";

const monorepoRoot = path.resolve(process.cwd(), "../..");

const nextConfig: NextConfig = {
  // Self-contained server bundle for the Docker image (see apps/web/Dockerfile).
  output: "standalone",
  outputFileTracingRoot: monorepoRoot,
  turbopack: { root: monorepoRoot },
  transpilePackages: ["@windsight/api-client"],
  poweredByHeader: false,
};

export default nextConfig;
