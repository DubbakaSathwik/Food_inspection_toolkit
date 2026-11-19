"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AuthLayout } from "@/components/auth-layout";
import { Icon } from "@/components/icon";
import { Button } from "@/components/ui";
import { FullPageLoader } from "@/components/shell";
import { homeFor, useAuth } from "@/lib/auth";

export default function PendingPage() {
  const { status, me, reload, signOut } = useAuth();
  const router = useRouter();
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    if (status === "signed_out") router.replace("/signin");
    if (status === "ready" && me?.status === "active") router.replace(homeFor(me));
  }, [status, me, router]);

  useEffect(() => {
    const t = window.setInterval(() => void reload(), 30000); // page updates when the account is activated
    return () => window.clearInterval(t);
  }, [reload]);

  if (status === "loading" || !me) return <FullPageLoader />;
  const declined = me.status === "declined";
  const disabled = me.status === "disabled";
  const steps: [string, "done" | "now" | "todo"][] = [
    ["Google sign-in complete", "done"],
    [
      declined
        ? "Request declined by an administrator"
        : disabled
          ? "Account disabled by an administrator"
          : "Waiting for administrator review",
      "now",
    ],
    ["Inspector workspace unlocked", "todo"],
  ];
  return (
    <AuthLayout>
      <div
        className="w-full max-w-[460px] rounded-[14px] border border-line bg-white p-7 flex flex-col gap-5 max-[760px]:p-5"
        aria-live="polite"
      >
        <span
          className="grid place-items-center rounded-[10px]"
          style={{
            width: 48,
            height: 48,
            background: declined || disabled ? "#F3DCD6" : "#FBEFD9",
            color: declined || disabled ? "#86301E" : "#7A4808",
          }}
        >
          <Icon name={declined || disabled ? "lock" : "clock"} size={22} />
        </span>
        <div className="flex flex-col gap-2">
          <h1 style={{ margin: 0, fontSize: 25, fontWeight: 800, letterSpacing: -0.4, lineHeight: 1.2 }}>
            {declined ? "Your access request was declined" : disabled ? "Your account is disabled" : "Your account is awaiting approval"}
          </h1>
          <p style={{ margin: 0, fontSize: 15, lineHeight: 1.6, color: "#55584E" }}>
            You&apos;re signed in as <strong style={{ color: "#20231D" }}>{me.email}</strong>.{" "}
            {declined || disabled
              ? "Contact your administrator if you think this is a mistake."
              : "An administrator needs to activate your account before you can start inspections."}
          </p>
        </div>
        <ul className="list-none m-0 p-0 flex flex-col gap-2.5" style={{ fontSize: 14 }}>
          {steps.map(([t, s]) => (
            <li
              key={t}
              className="flex items-center gap-2.5"
              style={{ color: s === "todo" ? "#686B60" : "#20231D", fontWeight: s === "now" ? 700 : 500 }}
            >
              {s === "done" ? (
                <Icon name="check" size={17} color="#56703A" />
              ) : (
                <span
                  aria-hidden
                  style={{ width: 16, height: 16, borderRadius: 8, border: `2px solid ${s === "now" ? "#B7862F" : "#D8D6C9"}` }}
                />
              )}
              {t}
            </li>
          ))}
        </ul>
        <p style={{ margin: 0, fontSize: 13, color: "#686B60", lineHeight: 1.6 }}>
          This page updates when your account is activated. You can close it and sign in again later.
        </p>
        <div className="flex flex-wrap gap-3 cs-acts">
          <Button
            iconRight="refresh"
            working={checking}
            onClick={async () => {
              setChecking(true);
              await reload();
              setChecking(false);
            }}
          >
            Check again
          </Button>
          <Button variant="secondary" onClick={() => void signOut().then(() => router.replace("/"))}>
            Sign out
          </Button>
        </div>
      </div>
    </AuthLayout>
  );
}
