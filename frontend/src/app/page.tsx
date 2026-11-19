"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Icon, type IconName } from "@/components/icon";
import { ImageSlot } from "@/components/media";
import { ButtonLink, Chip, Logo } from "@/components/ui";
import { homeFor, useAuth } from "@/lib/auth";

const SECTIONS = [
  { id: "home", label: "Home" },
  { id: "features", label: "Features" },
  { id: "how", label: "How It Works" },
  { id: "about", label: "About" },
];

const FEATURES: { icon: IconName; title: string; text: string }[] = [
  { icon: "box", title: "Scan Products", text: "Capture product packaging from multiple sides." },
  { icon: "shield", title: "Check Compliance", text: "Review product labels against configured FSSAI requirements." },
  { icon: "doc", title: "Generate Reports", text: "Create structured inspection reports with supporting evidence." },
];

const STEPS = [
  ["Upload Product Images", "Up to five photographs — front, back, sides and close-ups of the label."],
  ["Extract Label Information", "AI vision and OCR read product, manufacturer, licence, dates and declarations."],
  ["Review Inspection Findings", "Check reference matches, packaging differences and labelling findings. Correct anything uncertain."],
  ["Generate PDF Report", "Record your decision and create a print-ready report with the original photographs."],
];

const ABOUT = [
  "CRATE-SCAN is an independent inspection-support tool. It is not an official FSSAI or government portal.",
  "Licence and product checks compare against a demonstration reference database, not live government records.",
  "A packaging difference or a missing reference record is an observation for review — never proof of counterfeiting.",
  "Every finding shows its evidence and status, and the inspector records the final decision.",
];

function useScrollSpy(): string {
  const [active, setActive] = useState("home");
  useEffect(() => {
    const obs = new IntersectionObserver((entries) => entries.forEach((e) => e.isIntersecting && setActive(e.target.id)), {
      rootMargin: "-45% 0px -50% 0px",
    });
    SECTIONS.forEach((s) => {
      const el = document.getElementById(s.id);
      if (el) obs.observe(el);
    });
    return () => obs.disconnect();
  }, []);
  return active;
}

export default function Landing() {
  const active = useScrollSpy();
  const { status, me } = useAuth();
  const start = status === "ready" && me ? homeFor(me) : "/signin";
  const wrap = "mx-auto w-full max-w-[1200px] px-[clamp(16px,5vw,64px)] max-[760px]:px-4";
  return (
    <div>
      <main id="main">
        <div className={wrap}>
          <header
            className="flex flex-wrap items-center gap-4 py-[18px] max-[760px]:gap-y-2 max-[760px]:pt-3 max-[760px]:pb-2"
            style={{ animation: "csIn .5s ease both" }}
          >
            <Link href="/" className="no-underline">
              <span className="max-[760px]:hidden">
                <Logo size={34} text={21} />
              </span>
              <span className="hidden max-[760px]:block">
                <Logo size={28} text={17} />
              </span>
            </Link>
            <nav
              aria-label="Sections"
              className="flex items-center gap-1 mx-auto max-[760px]:order-3 max-[760px]:w-full max-[760px]:justify-between max-[760px]:border-t max-[760px]:border-line max-[760px]:pt-1.5 max-[760px]:gap-0.5"
            >
              {SECTIONS.map((s) => (
                <a
                  key={s.id}
                  href={`#${s.id}`}
                  className={`cs-navl max-[760px]:!px-2 max-[760px]:!text-[13px] whitespace-nowrap ${active === s.id ? "on" : ""}`}
                  aria-current={active === s.id ? "location" : undefined}
                >
                  {s.label}
                </a>
              ))}
            </nav>
            <ButtonLink href={start} className="max-[760px]:ml-auto max-[760px]:!min-h-10 max-[760px]:!px-4 max-[760px]:!text-[13.5px]">
              {status === "ready" ? "Open app" : "Get Started"}
            </ButtonLink>
          </header>

          <section
            id="home"
            className="grid grid-cols-[1fr_1.05fr] items-center gap-12 pt-[60px] pb-[84px] max-[960px]:grid-cols-1 max-[760px]:pt-5 max-[760px]:pb-11 max-[760px]:gap-7"
          >
            <div className="flex flex-col gap-6 min-w-0">
              <span className="flex items-center gap-3" style={{ fontSize: 12.5, fontWeight: 700, letterSpacing: 2.4, color: "#56703A" }}>
                AI-ASSISTED FOOD INSPECTION <span aria-hidden style={{ width: 48, height: 1.5, background: "#9CAB84" }} />
              </span>
              <h1 style={{ margin: 0, fontSize: "clamp(34px, 5.4vw, 64px)", fontWeight: 800, letterSpacing: -1.6, lineHeight: 1.04 }}>
                Smarter Food Product Inspections.
              </h1>
              <p style={{ margin: 0, fontSize: 17, lineHeight: 1.65, color: "#55584E", maxWidth: 520 }}>
                Examine packaged food products, review label information, identify potential irregularities, and generate structured
                inspection reports — all in one place.
              </p>
              <div className="flex flex-wrap gap-3 cs-acts">
                <ButtonLink href={start} iconRight="arrow">
                  Get Started
                </ButtonLink>
                <ButtonLink href="#features" variant="secondary">
                  Explore Features
                </ButtonLink>
              </div>
            </div>
            <div className="relative min-w-0">
              <div
                aria-hidden
                className="absolute -right-8 -top-4 bottom-0 w-3/4 rounded-[28px] max-[760px]:hidden"
                style={{ background: "#E3EACF" }}
              />
              <ImageSlot
                slot="hero"
                label="Hero photograph — packaged food product on a neutral tabletop. Replace in Admin › Settings › Website Images."
                className="relative h-[460px] max-[760px]:h-[300px]"
                style={{ borderRadius: 18 }}
              />
              <svg
                aria-hidden
                className="absolute pointer-events-none"
                style={{ left: "22%", top: "12%", width: "56%", height: "76%" }}
                viewBox="0 0 100 100"
                preserveAspectRatio="none"
                fill="none"
                stroke="#56703A"
                strokeLinecap="round"
              >
                <path
                  d="M0 14V2a2 2 0 0 1 2-2h12M86 0h12a2 2 0 0 1 2 2v12M100 86v12a2 2 0 0 1-2 2H86M14 100H2a2 2 0 0 1-2-2V86"
                  vectorEffect="non-scaling-stroke"
                  strokeWidth="2.6"
                />
              </svg>
              <span
                className="absolute right-[-12px] top-1/2 flex items-center gap-2 rounded-[10px] bg-white px-4 py-3 shadow-md max-[760px]:right-2"
                style={{ fontSize: 13.5, fontWeight: 700 }}
              >
                <Icon name="check" size={16} color="#56703A" /> Label scanned
              </span>
            </div>
          </section>
        </div>

        <section id="features" className="bg-white border-y border-line">
          <div className={`${wrap} grid grid-cols-3 max-[760px]:grid-cols-1 py-14 max-[760px]:py-8 gap-0 max-[760px]:gap-4`}>
            {FEATURES.map((f, i) => (
              <div
                key={f.title}
                className="cs-feat flex flex-col gap-3 px-8 max-[760px]:!px-[18px] max-[760px]:py-2"
                style={{ borderLeft: i ? "1px solid #E5E4DA" : undefined }}
              >
                <span className="max-[760px]:hidden" />
                <Icon name={f.icon} size={26} color="#56703A" />
                <h2 style={{ margin: 0, fontSize: 19, fontWeight: 700 }}>{f.title}</h2>
                <p style={{ margin: 0, fontSize: 14.5, lineHeight: 1.6, color: "#55584E", maxWidth: 280 }}>{f.text}</p>
              </div>
            ))}
          </div>
        </section>
        <style>{`@media (max-width:760px){#features .cs-feat{border-left:3px solid #9CAB84 !important}}`}</style>

        <div className={wrap}>
          <section id="how" className="flex flex-col gap-10 py-20 max-[760px]:py-12 max-[760px]:gap-6">
            <div className="flex flex-col gap-3">
              <span style={{ fontSize: 12.5, fontWeight: 700, letterSpacing: 2.4, color: "#56703A" }}>HOW IT WORKS</span>
              <h2
                style={{
                  margin: 0,
                  fontSize: "clamp(28px, 3.6vw, 40px)",
                  fontWeight: 800,
                  letterSpacing: -0.8,
                  lineHeight: 1.12,
                  maxWidth: 560,
                }}
              >
                From photographs to a structured report in four steps.
              </h2>
            </div>
            <ol className="grid grid-cols-4 gap-6 max-[960px]:grid-cols-2 max-[760px]:grid-cols-1 list-none p-0 m-0">
              {STEPS.map(([t, d], i) => (
                <li key={t} className="flex flex-col gap-2.5 pt-5" style={{ borderTop: `2px solid ${i === 0 ? "#56703A" : "#C5D89D"}` }}>
                  <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: 1.6, color: "#56703A" }}>STEP 0{i + 1}</span>
                  <h3 style={{ margin: 0, fontSize: 17, fontWeight: 700 }}>{t}</h3>
                  <p style={{ margin: 0, fontSize: 14.5, lineHeight: 1.6, color: "#55584E" }}>{d}</p>
                </li>
              ))}
            </ol>
          </section>

          <section
            className="grid grid-cols-[1fr_1.15fr] items-center gap-10 rounded-[18px] p-[clamp(20px,4vw,44px)] max-[960px]:grid-cols-1"
            style={{ background: "#E3EACF" }}
          >
            <div className="flex flex-col gap-4">
              <span style={{ fontSize: 12.5, fontWeight: 700, letterSpacing: 2.4, color: "#56703A" }}>THE INSPECTOR WORKSPACE</span>
              <h2 style={{ margin: 0, fontSize: "clamp(24px, 3vw, 32px)", fontWeight: 800, letterSpacing: -0.6, lineHeight: 1.18 }}>
                Every inspection, finding and report in one calm workspace.
              </h2>
              <p style={{ margin: 0, fontSize: 15.5, lineHeight: 1.6, color: "#55584E" }}>
                Start a new inspection in a click, return to recent records, and keep your reports organised by product, category and
                classification.
              </p>
            </div>
            <div
              className="rounded-[14px] bg-white shadow-xl overflow-hidden min-w-0"
              aria-label="Sample preview of the inspector workspace"
            >
              <div className="flex items-center justify-between px-5 py-3.5 border-b border-line">
                <Logo size={22} text={14} />
                <span style={{ fontSize: 11.5, fontWeight: 600, color: "#686B60" }}>Sample preview</span>
              </div>
              <div className="flex flex-col gap-4 p-5">
                <div className="grid grid-cols-3 gap-2.5">
                  {[
                    ["48", "Total inspections"],
                    ["3", "Pending reviews"],
                    ["2", "Proposals"],
                  ].map(([n, l]) => (
                    <div key={l} className="rounded-[10px] border border-line px-3 py-2.5">
                      <div style={{ fontSize: 18, fontWeight: 700 }}>{n}</div>
                      <div style={{ fontSize: 11.5, color: "#55584E" }}>{l}</div>
                    </div>
                  ))}
                </div>
                <div className="flex items-center justify-between gap-3 rounded-[10px] px-4 py-3" style={{ background: "#EEF2E1" }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 14 }}>Start a New Inspection</div>
                    <div style={{ fontSize: 12, color: "#55584E" }}>Upload product photographs</div>
                  </div>
                  <span className="cs-btn cs-btn-sm" aria-hidden style={{ minHeight: 32, fontSize: 12.5, padding: "6px 12px" }}>
                    Create Inspection
                  </span>
                </div>
                <div style={{ fontSize: 13, fontWeight: 700 }}>Recent inspections</div>
                {[
                  ["CS-0148", "Whole Grain Muesli", "Food Staples", "verified"],
                  ["CS-0147", "Spring Water 1 L", "Beverages", "not_verified"],
                  ["CS-0146", "Masala Peanuts", "Snacks", "suspicious"],
                ].map(([id, p, c, s]) => (
                  <div
                    key={id}
                    className="grid grid-cols-[70px_1fr_auto] max-[480px]:grid-cols-[1fr_auto] items-center gap-3 border-b border-rowline pb-2.5"
                    style={{ fontSize: 12.5 }}
                  >
                    <span className="max-[480px]:hidden" style={{ color: "#686B60" }}>
                      {id}
                    </span>
                    <span style={{ fontWeight: 700 }}>
                      {p}{" "}
                      <span className="max-[1100px]:hidden" style={{ fontWeight: 400, color: "#55584E" }}>
                        · {c}
                      </span>
                    </span>
                    <Chip status={s} />
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section id="about" className="grid grid-cols-2 gap-12 py-20 max-[960px]:grid-cols-1 max-[760px]:py-12 max-[760px]:gap-6">
            <div className="flex flex-col gap-4">
              <span style={{ fontSize: 12.5, fontWeight: 700, letterSpacing: 2.4, color: "#56703A" }}>ABOUT CRATE-SCAN</span>
              <h2 style={{ margin: 0, fontSize: "clamp(26px, 3.2vw, 34px)", fontWeight: 800, letterSpacing: -0.7, lineHeight: 1.15 }}>
                Built to support inspectors, not replace them.
              </h2>
              <p style={{ margin: 0, fontSize: 15.5, lineHeight: 1.65, color: "#55584E" }}>
                Designed to support inspection workflows with structured information and evidence-based findings. Final inspection decisions
                remain with the authorized inspector.
              </p>
            </div>
            <ul className="list-none m-0 p-0 flex flex-col">
              {ABOUT.map((t) => (
                <li key={t} className="flex gap-3 py-4 border-b border-line" style={{ fontSize: 14.5, lineHeight: 1.55, color: "#3a3d35" }}>
                  <Icon name="info" size={17} color="#56703A" />
                  <span>{t}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>
      </main>

      <footer className="bg-white border-t border-line">
        <div className={`${wrap} flex flex-wrap items-center justify-between gap-4 py-6`}>
          <Logo size={26} text={15} />
          <nav aria-label="Footer" className="flex flex-wrap gap-5" style={{ fontSize: 13.5 }}>
            {[
              ["#home", "Home"],
              ["#features", "Features"],
              ["#about", "About"],
              ["/signin", "Sign In"],
            ].map(([h, l]) => (
              <a key={l} href={h} style={{ color: "#55584E", textDecoration: "none" }}>
                {l}
              </a>
            ))}
          </nav>
          <span style={{ fontSize: 12.5, color: "#686B60" }}>© 2026 CRATE-SCAN · Inspection-support toolkit</span>
        </div>
      </footer>
    </div>
  );
}
