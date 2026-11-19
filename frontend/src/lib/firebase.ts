"use client";

import { type FirebaseApp, getApps, initializeApp } from "firebase/app";
import {
  type Auth,
  GoogleAuthProvider,
  browserLocalPersistence,
  connectAuthEmulator,
  getAuth,
  setPersistence,
  signInWithCredential,
  signInWithPopup,
  signInWithRedirect,
  signOut as fbSignOut,
} from "firebase/auth";
import { env, firebaseConfigured } from "./env";

let app: FirebaseApp | null = null;
let auth: Auth | null = null;

export function getFirebaseAuth(): Auth | null {
  if (typeof window === "undefined" || !firebaseConfigured) return null;
  if (!auth) {
    app = getApps()[0] ?? initializeApp(env.firebase);
    auth = getAuth(app);
    if (env.useAuthEmulator) connectAuthEmulator(auth, env.authEmulatorUrl, { disableWarnings: true });
    void setPersistence(auth, browserLocalPersistence);
    if (env.useAuthEmulator) {
      // Test-only helper (only exists when the Auth emulator is configured): sign in as a fake Google user.
      (window as unknown as { __csTestSignIn?: (email: string, name?: string) => Promise<void> }).__csTestSignIn = async (
        email: string,
        name = "Test User",
      ) => {
        const idToken = JSON.stringify({ sub: `sub-${email}`, email, email_verified: true, name });
        await signInWithCredential(auth!, GoogleAuthProvider.credential(idToken));
      };
    }
  }
  return auth;
}

/** Google sign-in: popup first, redirect fallback when the popup is blocked (Appendix E2). */
export async function signInWithGoogle(): Promise<void> {
  const a = getFirebaseAuth();
  if (!a) throw new Error("Sign-in is not configured. Set the NEXT_PUBLIC_FIREBASE_* variables.");
  const provider = new GoogleAuthProvider();
  provider.setCustomParameters({ prompt: "select_account" });
  try {
    await signInWithPopup(a, provider);
  } catch (e) {
    const code = (e as { code?: string }).code ?? "";
    if (code === "auth/popup-blocked" || code === "auth/operation-not-supported-in-this-environment") {
      await signInWithRedirect(a, provider);
      return;
    }
    if (code === "auth/popup-closed-by-user" || code === "auth/cancelled-popup-request") return;
    throw e;
  }
}

export async function signOut(): Promise<void> {
  const a = getFirebaseAuth();
  if (a) await fbSignOut(a);
}
