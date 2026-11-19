"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AuthLayout, GoogleMark } from "@/components/auth-layout";
import { Icon } from "@/components/icon";
import { ErrorBox } from "@/components/ui";
import { firebaseConfigured } from "@/lib/env";
import { homeFor, useAuth } from "@/lib/auth";

function safeNext(): string | null {
  if (typeof window === "undefined") return null;
  const n = new URLSearchParams(window.location.search).get("next");
  return n && n.startsWith("/") && !n.startsWith("//") ? n : null;
}

export default function SignInPage() {
  const { status, me, signIn, error } = useAuth();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (status === "ready" && me) {
      const home = homeFor(me);
      const next = safeNext();
      router.replace(next && home !== "/pending" && next.startsWith(home) ? next : home);
    }
  }, [status, me, router]);

  async function go() {
    setErr(null);
    setBusy(true);
    try {
      await signIn();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Sign-in failed. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout>
      <div className="w-full max-w-[420px] rounded-[14px] border border-line bg-white p-7 flex flex-col gap-5 max-[760px]:p-5">
        <div className="flex flex-col gap-2">
          <h1 style={{ margin: 0, fontSize: 26, fontWeight: 800, letterSpacing: -0.4 }}>Get started</h1>
          <p style={{ margin: 0, fontSize: 15, lineHeight: 1.6, color: "#55584E" }}>
            Sign in with your Google account to open your inspection workspace.
          </p>
        </div>
        <button
          type="button"
          className={`cs-btn2 w-full ${busy || status === "loading" ? "cs-working" : ""}`}
          onClick={go}
          disabled={!firebaseConfigured || busy}
        >
          <GoogleMark /> Continue with Google
        </button>
        {!firebaseConfigured && <ErrorBox error="Sign-in is not configured for this site yet (missing Firebase settings)." />}
        {(err || (status === "error" && error)) && <ErrorBox error={err ?? error ?? ""} />}
        <div
          className="flex gap-3 rounded-[10px] border border-line p-4"
          style={{ background: "#FBF8F0", fontSize: 13.5, lineHeight: 1.6, color: "#55584E" }}
        >
          <Icon name="info" size={17} />
          <span>
            New accounts are reviewed by an administrator before access is granted. Roles are assigned by administrators — they cannot be
            chosen at sign-in.
          </span>
        </div>
        <p style={{ margin: 0, fontSize: 12.5, color: "#686B60" }}>
          By continuing you agree to use CRATE-SCAN for authorised inspection work only.
        </p>
      </div>
    </AuthLayout>
  );
}
