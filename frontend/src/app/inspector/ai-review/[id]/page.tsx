"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { Icon } from "@/components/icon";
import { Stepper } from "@/components/inspection";
import { PageHeader } from "@/components/shell";
import { Backlink, Button, CATEGORY_LABELS, ErrorBox, LoadingBlock, Panel, Pill } from "@/components/ui";
import { ApiError, api, type Inspection } from "@/lib/api";

const STEPS = [
  ["Preparing approved values", "Your confirmed and corrected fields are packaged for analysis."],
  ["Matching the reference database", "Product, brand, variant and manufacturer compared with demonstration records."],
  ["Checking the demo licence record", "Licence number, validity and status looked up in demonstration data."],
  ["Comparing packaging", "Uploaded photographs compared with reference packaging images."],
  ["Applying labelling rules", "Category rules run against the approved values."],
  ["Assembling findings", "Observations, evidence and rule references collected for your review."],
] as const;

export default function AIReviewPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [d, setD] = useState<Inspection | null>(null);
  const [step, setStep] = useState(0);
  const [done, setDone] = useState(false);
  const [err, setErr] = useState<ApiError | null>(null);
  const [skip, setSkip] = useState(false);
  const started = useRef(false);

  const run = useCallback(async () => {
    setErr(null);
    setDone(false);
    setStep(0);
    try {
      const res = await api<Inspection>(`/api/v1/inspections/${id}/analyze`, { method: "POST" });
      setD(res);
      setDone(true);
    } catch (e) {
      setErr(e instanceof ApiError ? e : new ApiError(0, "error", "Analysis failed."));
    }
  }, [id]);

  useEffect(() => {
    api<Inspection>(`/api/v1/inspections/${id}`)
      .then((x) => {
        setD(x);
        if (x.status === "completed") router.replace(`/inspector/report/${id}`);
        else if (!started.current) {
          started.current = true;
          void run();
        }
      })
      .catch((e) => setErr(e instanceof ApiError ? e : new ApiError(0, "error", "Could not load the inspection.")));
  }, [id, router, run]);

  // Animation advances on a timer but holds on the last step until the request resolves.
  useEffect(() => {
    if (err) return;
    const t = window.setInterval(() => setStep((s) => (s < STEPS.length - 1 ? s + 1 : s)), 1300);
    return () => window.clearInterval(t);
  }, [err, done]);

  const finished = done && (step >= STEPS.length - 1 || skip);
  useEffect(() => {
    if (finished) {
      const t = window.setTimeout(() => router.push(`/inspector/findings/${id}`), skip ? 0 : 1200);
      return () => window.clearTimeout(t);
    }
  }, [finished, skip, router, id]);

  const fields = d?.fields ?? [];
  const product = fields.find((f) => f.key === "product_name")?.value;
  const brand = fields.find((f) => f.key === "brand")?.value;
  const qty = fields.find((f) => f.key === "net_quantity")?.value;
  const shown = finished ? STEPS.length : step + 1;

  return (
    <>
      <PageHeader
        title="AI Review"
        subtitle="Running reference, licence, packaging and labelling checks on your approved values."
        back={<Backlink href={`/inspector/verify/${id}`}>Back to verification</Backlink>}
        actions={<Pill>Step 3 of 5</Pill>}
      />
      <Stepper current={3} />
      <div className="grid grid-cols-[minmax(0,1fr)_300px] gap-5 items-start max-[960px]:grid-cols-1">
        <Panel>
          {err ? (
            <div className="flex flex-col gap-4">
              <ErrorBox error={err.message} />
              {err.code === "fields_unconfirmed" || err.code === "invalid_state" ? (
                <Link href={`/inspector/verify/${id}`} className="cs-btn self-start">
                  Go back to Verify Fields
                </Link>
              ) : (
                <p className="m-0" style={{ fontSize: 14, color: "#55584E" }}>
                  Your photographs and approved values are saved. Retry now, or come back later from the dashboard.
                </p>
              )}
              {err.code !== "fields_unconfirmed" && err.code !== "invalid_state" && (
                <div className="flex gap-3 cs-acts">
                  <Button icon="refresh" onClick={() => void run()}>
                    Retry analysis
                  </Button>
                </div>
              )}
            </div>
          ) : (
            <>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="cs-h2">{finished ? "Analysis complete" : `Analysing — step ${shown} of ${STEPS.length}`}</h2>
                {!finished && (
                  <Button small variant="secondary" onClick={() => setSkip(true)} disabled={!done}>
                    Skip animation
                  </Button>
                )}
                {finished && (
                  <Button small iconRight="arrow" onClick={() => router.push(`/inspector/findings/${id}`)}>
                    View findings
                  </Button>
                )}
              </div>
              <div
                className="mt-4 h-2 rounded-full"
                style={{ background: "#EEF2E1" }}
                role="progressbar"
                aria-valuenow={shown}
                aria-valuemax={STEPS.length}
                aria-label="Analysis progress"
              >
                <div
                  className="h-2 rounded-full"
                  style={{
                    width: `${(shown / STEPS.length) * (finished ? 100 : 92)}%`,
                    background: "#56703A",
                    transition: "width .6s ease",
                  }}
                />
              </div>
              <div
                className="mt-4 flex flex-wrap items-center gap-6 rounded-[12px] p-5"
                style={{ background: "#E3EACF", border: "1px solid #C5D89D" }}
                aria-live="polite"
              >
                <div className="relative shrink-0" style={{ width: 110, height: 110 }} aria-hidden>
                  <div
                    className="absolute inset-0 rounded-full"
                    style={{ border: "2px dashed #9CAB84", animation: finished ? "none" : "csOrbit 7s linear infinite" }}
                  >
                    <span className="absolute rounded-full" style={{ width: 10, height: 10, background: "#56703A", top: 10, left: 10 }} />
                  </div>
                  <div className="absolute grid place-items-center rounded-[14px] bg-white overflow-hidden" style={{ inset: 26 }}>
                    <Icon name={finished ? "check" : "scan"} size={28} color="#56703A" />
                    {!finished && (
                      <span
                        className="absolute left-1 right-1 h-0.5"
                        style={{ background: "#56703A", animation: "csScan 2s ease-in-out infinite" }}
                      />
                    )}
                  </div>
                </div>
                <div className="flex-1 min-w-[200px] flex flex-col gap-2">
                  <span style={{ fontSize: 11.5, fontWeight: 700, letterSpacing: 1.6, color: "#56703A" }}>
                    {finished ? "DONE" : "AI IS WORKING"}
                  </span>
                  <strong style={{ fontSize: 17 }}>
                    {finished ? "Findings are ready for your review" : STEPS[step][0]}
                    {!finished && (
                      <span className="cs-dots">
                        <span>.</span>
                        <span>.</span>
                        <span>.</span>
                      </span>
                    )}
                  </strong>
                  <p className="m-0" style={{ fontSize: 13.5, color: "#55584E", lineHeight: 1.5 }}>
                    Your photographs and approved values stay saved. The AI only suggests; the final decision remains yours.
                  </p>
                </div>
              </div>
              <ol className="mt-4 list-none m-0 p-0 flex flex-col gap-2.5">
                {STEPS.map(([t, s], i) => {
                  const state = finished || i < step ? "done" : i === step ? "now" : "todo";
                  return (
                    <li
                      key={t}
                      className="flex gap-3 rounded-[10px] px-4 py-3.5"
                      style={{
                        border: `1px solid ${state === "now" ? "#9CAB84" : "#E5E4DA"}`,
                        background: state === "now" ? "#EEF2E1" : "#fff",
                        opacity: state === "todo" ? 0.6 : 1,
                      }}
                    >
                      <span
                        className="grid place-items-center shrink-0 rounded-full"
                        style={{
                          width: 24,
                          height: 24,
                          fontSize: 12,
                          fontWeight: 700,
                          background: state === "todo" ? "#ECEAE2" : "#3E5228",
                          color: state === "todo" ? "#686B60" : "#fff",
                        }}
                      >
                        {state === "done" ? <Icon name="tick" size={13} /> : i + 1}
                      </span>
                      <div className="flex flex-col gap-0.5">
                        <strong style={{ fontSize: 14.5 }}>{t}</strong>
                        <span style={{ fontSize: 13, color: "#55584E" }}>{s}</span>
                        {state === "now" && (
                          <span
                            className="inline-flex items-center gap-1.5 mt-1"
                            style={{ fontSize: 12.5, fontWeight: 700, color: "#3B5420" }}
                          >
                            <span className="cs-ring" style={{ width: 12, height: 12, borderWidth: 2 }} />
                            Working
                          </span>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ol>
            </>
          )}
        </Panel>
        <div className="flex flex-col gap-5">
          <aside className="cs-panel" aria-label="Product under analysis">
            <h2 style={{ margin: "0 0 12px", fontSize: 16, fontWeight: 700 }}>Product under analysis</h2>
            {!d ? (
              <LoadingBlock rows={3} />
            ) : (
              <>
                <strong style={{ fontSize: 15 }}>{product ?? "Untitled product"}</strong>
                <div style={{ fontSize: 13, color: "#55584E" }}>{[brand, qty].filter(Boolean).join(" · ")}</div>
                <div style={{ fontSize: 13, color: "#55584E" }}>{d.category ? CATEGORY_LABELS[d.category] : "—"}</div>
                <dl className="mt-3 grid grid-cols-[1fr_auto] gap-y-1.5 m-0" style={{ fontSize: 13 }}>
                  {[
                    ["Inspection", d.id],
                    ["Photographs", d.photos.length],
                    ["Fields approved", fields.filter((f) => f.value).length],
                    ["Corrections", fields.filter((f) => f.status === "edited").length],
                    ["Marked not present", fields.filter((f) => !f.value).length],
                  ].map(([k, v]) => (
                    <div key={String(k)} className="contents">
                      <dt style={{ color: "#55584E" }}>{k}</dt>
                      <dd className="m-0 text-right font-bold">{v}</dd>
                    </div>
                  ))}
                </dl>
              </>
            )}
          </aside>
          <aside className="cs-panel" aria-label="If analysis fails">
            <h2 style={{ margin: "0 0 8px", fontSize: 16, fontWeight: 700 }}>If analysis fails</h2>
            <p className="m-0" style={{ fontSize: 13.5, color: "#55584E", lineHeight: 1.55 }}>
              If an AI provider is unavailable, the inspection is saved with your approved values. You can retry the analysis without losing
              the photographs or your checks.
            </p>
          </aside>
        </div>
      </div>
    </>
  );
}
