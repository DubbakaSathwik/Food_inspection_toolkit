import type { NextConfig } from "next";

// Auth is client-side (Firebase ID token in the browser, no session cookies), so app pages are
// client-rendered; Cache Components / partial prefetching are not used (DECISIONS T-23).

function origin(url: string | undefined): string | null {
  try {
    return url ? new URL(url).origin : null;
  } catch {
    return null;
  }
}

/** Security headers (moved from netlify.toml when hosting moved to Render, DECISIONS T-40). Production only:
 *  the dev server needs eval for hot reload. connect-src/img-src follow NEXT_PUBLIC_API_BASE_URL. */
function securityHeaders() {
  const api = origin(process.env.NEXT_PUBLIC_API_BASE_URL);
  const emulator =
    process.env.NEXT_PUBLIC_USE_AUTH_EMULATOR === "true"
      ? origin(process.env.NEXT_PUBLIC_AUTH_EMULATOR_URL ?? "http://127.0.0.1:9099")
      : null;
  const connect = [
    "'self'",
    api,
    emulator,
    "https://identitytoolkit.googleapis.com",
    "https://securetoken.googleapis.com",
    "https://www.googleapis.com",
  ];
  const csp = [
    "default-src 'self'",
    // Next.js inline bootstrap scripts and the design's inline styles need 'unsafe-inline' (no nonce pipeline yet).
    "script-src 'self' 'unsafe-inline' https://apis.google.com",
    "style-src 'self' 'unsafe-inline'",
    `img-src ${["'self'", "data:", "blob:", api, "https://lh3.googleusercontent.com"].filter(Boolean).join(" ")}`,
    "font-src 'self' data:",
    `connect-src ${connect.filter(Boolean).join(" ")}`,
    "frame-src https://*.firebaseapp.com https://accounts.google.com",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
  ].join("; ");
  return [
    // CSP_REPORT_ONLY=true (Render env var) only reports violations in the browser console instead of blocking:
    // a safety valve if real Google sign-in is blocked by the policy.
    { key: process.env.CSP_REPORT_ONLY === "true" ? "Content-Security-Policy-Report-Only" : "Content-Security-Policy", value: csp },
    { key: "X-Content-Type-Options", value: "nosniff" },
    { key: "X-Frame-Options", value: "DENY" },
    { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
    { key: "Permissions-Policy", value: "camera=(self), microphone=(), geolocation=()" },
    { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
  ];
}

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  devIndicators: false,
  async headers() {
    return process.env.NODE_ENV === "production" ? [{ source: "/:path*", headers: securityHeaders() }] : [];
  },
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
