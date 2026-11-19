// Browser-safe configuration only (NEXT_PUBLIC_*). Firebase web config is public by design.
export const env = {
  apiBase: (process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000").replace(/\/$/, ""),
  firebase: {
    apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || "",
    authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || "",
    projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "",
    appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || "",
  },
  useAuthEmulator: process.env.NEXT_PUBLIC_USE_AUTH_EMULATOR === "true",
  authEmulatorUrl: process.env.NEXT_PUBLIC_AUTH_EMULATOR_URL || "http://127.0.0.1:9099",
};

export const firebaseConfigured = Boolean(env.firebase.apiKey && env.firebase.projectId);
