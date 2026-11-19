"use client";

import { onIdTokenChanged, type User } from "firebase/auth";
import { usePathname, useRouter } from "next/navigation";
import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { ApiError, api, onAuthProblem, type Me } from "./api";
import { firebaseConfigured } from "./env";
import { getFirebaseAuth, signInWithGoogle, signOut as fbSignOut } from "./firebase";

type Status = "loading" | "signed_out" | "ready" | "error";
type Ctx = {
  status: Status;
  user: User | null;
  me: Me | null;
  error: string | null;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
  reload: () => Promise<void>;
};

const AuthContext = createContext<Ctx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>(firebaseConfigured ? "loading" : "signed_out");
  const [user, setUser] = useState<User | null>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadMe = useCallback(async (u: User) => {
    try {
      let profile = await api<Me>("/api/v1/me");
      if (profile.claims_stale) {
        await u.getIdToken(true); // pick up the role/active claims the server just set
        profile = await api<Me>("/api/v1/me");
      }
      setMe(profile);
      setError(null);
      setStatus("ready");
    } catch (e) {
      setMe(null);
      setError(e instanceof ApiError ? e.message : "Could not load your account.");
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    const auth = getFirebaseAuth();
    if (!auth) return;
    return onIdTokenChanged(auth, (u) => {
      setUser(u);
      if (!u) {
        setMe(null);
        setStatus("signed_out");
      } else if (!me || me.uid !== u.uid) {
        setStatus("loading");
        void loadMe(u);
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadMe]);

  useEffect(
    () =>
      onAuthProblem((code) => {
        const u = getFirebaseAuth()?.currentUser;
        if (code.startsWith("account_") && u) void loadMe(u);
      }),
    [loadMe],
  );

  const value = useMemo<Ctx>(
    () => ({
      status,
      user,
      me,
      error,
      signIn: signInWithGoogle,
      signOut: async () => {
        await fbSignOut();
        setMe(null);
        setStatus("signed_out");
      },
      reload: async () => {
        const u = getFirebaseAuth()?.currentUser;
        if (u) await loadMe(u);
      },
    }),
    [status, user, me, error, loadMe],
  );
  return <AuthContext value={value}>{children}</AuthContext>;
}

export function useAuth(): Ctx {
  const c = useContext(AuthContext);
  if (!c) throw new Error("useAuth must be used inside AuthProvider");
  return c;
}

export type Area = "inspector" | "admin";

export function homeFor(me: Me | null): string {
  if (!me || me.status !== "active") return "/pending";
  return me.role === "inspector" ? "/inspector" : "/admin";
}

/** Client-side route guard. The backend enforces every permission independently. */
export function useGuard(area: Area): { allowed: boolean; me: Me | null } {
  const { status, me } = useAuth();
  const router = useRouter();
  const path = usePathname();
  const allowed =
    status === "ready" &&
    !!me &&
    me.status === "active" &&
    (area === "inspector" ? me.role === "inspector" : me.role === "admin" || me.role === "super_admin");
  useEffect(() => {
    if (status === "signed_out") router.replace(`/signin?next=${encodeURIComponent(path)}`);
    else if (status === "ready" && me && !allowed) router.replace(homeFor(me));
  }, [status, me, allowed, router, path]);
  return { allowed, me };
}
