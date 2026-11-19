import type { NextConfig } from "next";

// Auth is client-side (Firebase ID token in the browser, no session cookies), so app pages are
// client-rendered; Cache Components / partial prefetching are not used (DECISIONS T-23).
const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  devIndicators: false,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
