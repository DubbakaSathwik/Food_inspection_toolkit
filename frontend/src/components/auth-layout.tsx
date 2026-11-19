"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { ImageSlot } from "./media";
import { Logo } from "./ui";

/** Split layout used by SignIn and Pending (side image slot `signin`). */
export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="grid min-h-screen grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] max-[760px]:grid-cols-1">
      <aside className="flex flex-col gap-6 p-8 max-[760px]:p-4 max-[760px]:gap-4" style={{ background: "#E3EACF" }}>
        <Link href="/" className="no-underline">
          <Logo />
        </Link>
        <ImageSlot
          slot="signin"
          label="Supporting photograph — packaged food products on a shelf. Replace in Admin › Settings › Website Images."
          className="flex-1 min-h-[420px] max-[760px]:min-h-[180px] max-[760px]:max-h-[220px]"
        />
        <p className="m-0 max-w-[360px]" style={{ fontSize: 14, lineHeight: 1.6, color: "#55584E" }}>
          An inspection-support toolkit. Findings are presented for review — final decisions stay with the authorized inspector.
        </p>
      </aside>
      <main id="main" className="grid place-items-center p-8 max-[760px]:p-4 max-[760px]:pb-10">
        {children}
      </main>
    </div>
  );
}

export function GoogleMark() {
  return (
    <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden>
      <path
        fill="#FFC107"
        d="M43.6 20.5H42V20H24v8h11.3C33.7 32.6 29.3 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z"
      />
      <path
        fill="#FF3D00"
        d="M6.3 14.7l6.6 4.8C14.6 15.1 18.9 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"
      />
      <path
        fill="#4CAF50"
        d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.3 0-9.7-3.4-11.3-8.1l-6.5 5C9.5 39.6 16.2 44 24 44z"
      />
      <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z" />
    </svg>
  );
}
