"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Icon, type IconName } from "@/components/icon";
import { Stepper } from "@/components/inspection";
import { AuthImage } from "@/components/media";
import { PageHeader } from "@/components/shell";
import {
  Backlink,
  Button,
  CATEGORY_LABELS,
  Chip,
  ErrorBox,
  fmtDate,
  label,
  LoadingBlock,
  Notice,
  Panel,
  Pill,
  TextArea,
  TextLink,
} from "@/components/ui";
import { api, errorMessage, type Finding, type Inspection } from "@/lib/api";

type Analysis = {
  reference?: {
    status: string;
    detail: string;
    record_id?: string | null;
    record_label?: string | null;
    comparisons?: { field: string; extracted: string; reference: string; result: string }[];
  };
  licence?: { status: string; label: string; detail: string };
  packaging?: {
    status: string;
    summary: string;
    observations: { area: string; observation: string; severity: string }[];
    version?: string;
    record_id?: string;
  };
  compliance?: { results: { result: string; claim: boolean }[]; passed: number };
};

const ACTIONS: Record<string, [string, string]> = {
  compliance: ["Confirm issue", "Mark as present"],
  claim: ["Flag claim", "Not an issue"],
  packaging: ["Treat as suspicious", "Normal variation"],
  reference: ["Confirm finding", "Dismiss"],
  licence: ["Confirm finding", "Dismiss"],
  extraction: ["Confirm finding", "Dismiss"],
};
const CLASSES = [
  ["verified", "Verified", "Matches reference records and no open labelling issues."],
  ["not_verified", "Not verified", "Could not be fully confirmed — missing information or open issues."],
  ["suspicious", "Suspicious", "Differences that need further investigation."],
] as const;

function FindingCard({
  f,
  onDecide,
}: {
  f: Finding;
  onDecide: (body: { action: string; corrected_value?: string; note?: string }) => Promise<void>;
}) {
  const [mode, setMode] = useState<"none" | "correct" | "note">("none");
  const [value, setValue] = useState(f.extracted ?? "");
  const [note, setNote] = useState(f.decision?.note ?? "");
  const [busy, setBusy] = useState(false);
  const [yes, no] = ACTIONS[f.kind] ?? ACTIONS.reference;
  const tone = f.severity === "high" ? "#B4533A" : f.severity === "warning" ? "#C9893A" : "#9CAB84";
  const go = async (body: { action: string; corrected_value?: string; note?: string }) => {
    setBusy(true);
    try {
      await onDecide(body);
      setMode("none");
    } finally {
      setBusy(false);
    }
  };
  const dec = f.decision;
  return (
    <article
      className="cs-panel flex flex-col gap-3"
      style={{ borderLeft: `4px solid ${dec ? "#9CAB84" : tone}`, padding: 20 }}
      aria-label={f.title}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 style={{ margin: 0, fontSize: 15.5, fontWeight: 700 }}>{f.title}</h3>
        {dec ? (
          <Chip tone="ok" dot={false}>
            {dec.action === "accepted" ? yes : dec.action === "dismissed" ? no : "Corrected"}
          </Chip>
        ) : (
          <Chip tone={f.severity === "high" ? "bad" : f.severity === "warning" ? "warn" : "neu"} dot={false}>
            {f.kind === "packaging" ? "Observation" : f.status_label}
          </Chip>
        )}
      </div>
      <div className="grid grid-cols-3 gap-4 max-[760px]:grid-cols-1" style={{ fontSize: 13.5, lineHeight: 1.5 }}>
        <div>
          <div className="cs-label">Expected</div>
          <div>{f.expected ?? "—"}</div>
        </div>
        <div>
          <div className="cs-label">Found on pack</div>
          <div style={{ overflowWrap: "anywhere" }}>{f.extracted ?? "Not found on photographs"}</div>
          <div style={{ color: "#55584E" }}>{f.detail}</div>
        </div>
        <div>
          <div className="cs-label">Rule reference</div>
          <div>
            {f.rule_code
              ? `Demo rule ${f.rule_code} · based on ${f.rule_reference}`
              : f.kind === "packaging"
                ? "Packaging reference comparison · demonstration images"
                : "Demonstration reference data"}
          </div>
        </div>
      </div>
      <div style={{ fontSize: 13.5 }}>
        <span className="cs-label">Evidence</span>
        <div>{f.evidence_photo ? `Photo ${f.evidence_photo}` : "Extracted values"}</div>
      </div>
      {dec?.action === "corrected" && (
        <div className="rounded-[8px] px-3 py-2" style={{ background: "#E2E8EE", color: "#2F4A63", fontSize: 13.5 }}>
          Your correction: <strong>{dec.corrected_value}</strong> · Original AI value kept:{" "}
          <strong>{f.ai_original ?? f.extracted ?? "not found"}</strong>
        </div>
      )}
      {dec?.note && <div style={{ fontSize: 13, color: "#55584E" }}>Your comment: {dec.note}</div>}
      {mode === "correct" && (
        <div className="flex flex-col gap-2">
          <label className="cs-label" htmlFor={`c-${f.id}`}>
            Corrected value (the AI value stays in the record)
          </label>
          <input id={`c-${f.id}`} className="cs-input" value={value} onChange={(e) => setValue(e.target.value)} maxLength={2000} />
          <input
            aria-label="Comment"
            className="cs-input"
            placeholder="Comment (optional)"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            maxLength={2000}
          />
          <div className="flex gap-2 cs-acts">
            <Button
              small
              working={busy}
              disabled={!value.trim()}
              onClick={() => void go({ action: "corrected", corrected_value: value.trim(), note: note.trim() || undefined })}
            >
              Save correction
            </Button>
            <Button small variant="secondary" onClick={() => setMode("none")}>
              Cancel
            </Button>
          </div>
        </div>
      )}
      {mode === "note" && (
        <div className="flex flex-col gap-2">
          <input
            aria-label="Reason"
            className="cs-input"
            placeholder={`Why: ${no.toLowerCase()} (optional)`}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            maxLength={2000}
            autoFocus
          />
          <div className="flex gap-2 cs-acts">
            <Button small working={busy} onClick={() => void go({ action: "dismissed", note: note.trim() || undefined })}>
              {no}
            </Button>
            <Button small variant="secondary" onClick={() => setMode("none")}>
              Cancel
            </Button>
          </div>
        </div>
      )}
      {mode === "none" && (
        <div className="flex flex-wrap gap-2 cs-acts">
          <Button
            small
            icon="flag"
            working={busy}
            variant={dec?.action === "accepted" ? "secondary" : "primary"}
            onClick={() => void go({ action: "accepted", note: note.trim() || undefined })}
          >
            {yes}
          </Button>
          <Button small variant="secondary" onClick={() => setMode("note")}>
            {no}
          </Button>
          {f.kind !== "packaging" && (
            <Button small variant="secondary" icon="edit" onClick={() => setMode("correct")}>
              Correct value
            </Button>
          )}
        </div>
      )}
    </article>
  );
}

function Summary({
  icon,
  title,
  value,
  detail,
  tone,
}: {
  icon: IconName;
  title: string;
  value: string;
  detail: string;
  tone: "ok" | "warn" | "neu" | "bad";
}) {
  const bg = { ok: "#EEF2E1", warn: "#FBF3E6", neu: "#F4F2EA", bad: "#F8E8E3" }[tone];
  const fg = { ok: "#3B5420", warn: "#7A4808", neu: "#4D4F46", bad: "#86301E" }[tone];
  return (
    <div className="flex flex-col gap-1.5 rounded-[12px] border border-line p-4 min-w-0" style={{ background: bg }}>
      <span className="flex items-center gap-1.5" style={{ fontSize: 12.5, fontWeight: 700, color: "#55584E" }}>
        <Icon name={icon} size={15} />
        {title}
      </span>
      <strong style={{ fontSize: 16, color: fg, lineHeight: 1.3 }}>{value}</strong>
      <span style={{ fontSize: 12.5, color: "#55584E", lineHeight: 1.45 }}>{detail}</span>
    </div>
  );
}

export default function FindingsPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [d, setD] = useState<Inspection | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [photo, setPhoto] = useState(0);
  const [choice, setChoice] = useState<string | null>(null);
  const [remarks, setRemarks] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api<Inspection>(`/api/v1/inspections/${id}`)
      .then((x) => {
        if (x.status === "completed") router.replace(`/inspector/report/${id}`);
        else if (x.status !== "analysed") router.replace(`/inspector/verify/${id}`);
        setD(x);
        setChoice(x.decision?.classification ?? null);
        setRemarks(x.decision?.remarks ?? "");
        setSaved(!!x.decision);
      })
      .catch((e) => setErr(errorMessage(e)));
  }, [id, router]);

  async function decide(fid: string, body: object) {
    try {
      setD(await api<Inspection>(`/api/v1/inspections/${id}/findings/${fid}`, { method: "PATCH", body }));
    } catch (e) {
      setErr(errorMessage(e));
    }
  }
  async function saveDecision(thenReport: boolean) {
    if (!choice) return;
    setSaving(true);
    setErr(null);
    try {
      setD(await api<Inspection>(`/api/v1/inspections/${id}/decision`, { method: "PUT", body: { classification: choice, remarks } }));
      setSaved(true);
      if (thenReport) router.push(`/inspector/report/${id}`);
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  if (!d)
    return (
      <>
        <PageHeader title="Findings" />
        {err ? (
          <ErrorBox error={err} />
        ) : (
          <Panel>
            <LoadingBlock rows={6} />
          </Panel>
        )}
      </>
    );
  const a = (d.analysis ?? {}) as Analysis;
  const f = Object.fromEntries(d.fields.map((x) => [x.key, x]));
  const open = d.findings.filter((x) => !x.decision);
  const comp = a.compliance?.results ?? [];
  const failN = comp.filter((r) => r.result === "fail").length;
  const claimN = comp.filter((r) => r.claim && r.result === "review").length;
  const obs = a.packaging?.observations ?? [];
  const sug = d.suggestion;
  const keyFields = ["product_name", "brand", "manufacturer_name", "fssai_licence", "net_quantity", "mrp", "batch", "expiry"];

  return (
    <>
      <PageHeader
        title={f.product_name?.value ?? "Findings"}
        back={<Backlink href={`/inspector/verify/${id}`}>Back to field verification</Backlink>}
        subtitle={[d.id, d.category ? CATEGORY_LABELS[d.category] : null, fmtDate(d.created_at, true), `${d.photos.length} photographs`]
          .filter(Boolean)
          .join(" · ")}
        actions={<Pill>Step 4 of 5</Pill>}
      />
      <Stepper current={4} />
      {err && <ErrorBox error={err} />}
      {d.analysis_stale && (
        <Notice tone="warn" icon="alert">
          Fields were changed after the analysis. <Link href={`/inspector/ai-review/${id}`}>Run the AI review again</Link> before deciding.
        </Notice>
      )}

      <section className="flex flex-col gap-3" aria-label="Photographs">
        <div className="cs-strip" role="tablist" aria-label="Photo switcher">
          {d.photos.map((p, i) => (
            <button
              key={p.id}
              type="button"
              role="tab"
              aria-selected={photo === i}
              onClick={() => setPhoto(i)}
              className="flex flex-col items-center gap-1.5 rounded-[10px] p-2 cursor-pointer bg-white"
              style={{
                width: 88,
                border: `${photo === i ? 2 : 1}px solid ${photo === i ? "#56703A" : "#E5E4DA"}`,
                background: photo === i ? "#EEF2E1" : "#fff",
              }}
            >
              <span className="block overflow-hidden rounded-[6px]" style={{ width: 70, height: 60, background: "#E8E5DA" }}>
                <AuthImage
                  path={d.photos_deleted ? null : `/api/v1/inspections/${id}/photos/${p.id}?thumb=true`}
                  alt={`Photo ${i + 1}`}
                  style={{ objectFit: "cover" }}
                />
              </span>
              <span style={{ fontSize: 11, fontWeight: 600, whiteSpace: "nowrap" }}>
                Photo {i + 1} · {label(p.label)}
              </span>
            </button>
          ))}
        </div>
        {d.photos[photo] && (
          <div className="flex flex-wrap items-center gap-5 rounded-[12px] border border-line p-3" style={{ background: "#FBF8F0" }}>
            <div className="overflow-hidden rounded-[8px]" style={{ width: 220, height: 170, background: "#E8E5DA" }}>
              <AuthImage
                path={d.photos_deleted ? null : `/api/v1/inspections/${id}/photos/${d.photos[photo].id}`}
                alt={`Photo ${photo + 1}`}
              />
            </div>
            <div className="flex-1 min-w-[200px]">
              <strong style={{ fontSize: 14 }}>Now showing</strong>
              <p className="m-0 mt-1" style={{ fontSize: 13.5, color: "#55584E" }}>
                Photo {photo + 1} · {label(d.photos[photo].label)}. Select another photograph to compare it with a finding.
              </p>
            </div>
          </div>
        )}
      </section>

      <div className="grid gap-3 cs-grid" style={{ gridTemplateColumns: "repeat(5, minmax(0, 1fr))" }}>
        <Summary
          icon="doc"
          title="Extraction"
          tone="ok"
          value={`${d.fields.filter((x) => x.value).length} fields approved`}
          detail={`${d.fields.filter((x) => x.status === "edited").length} corrected · ${d.fields.filter((x) => !x.value).length} not present`}
        />
        <Summary
          icon="box"
          title="Reference match"
          tone={a.reference?.status === "exact" ? "ok" : a.reference?.status === "mismatch" ? "bad" : "warn"}
          value={label(a.reference?.status)}
          detail={a.reference?.record_label ? `Demo record: ${a.reference.record_label}` : (a.reference?.detail ?? "")}
        />
        <Summary
          icon="shield"
          title="Licence (demo)"
          tone={
            a.licence?.status === "found"
              ? "ok"
              : ["expired", "suspended", "invalid_format"].includes(a.licence?.status ?? "")
                ? "bad"
                : "warn"
          }
          value={a.licence?.label ?? "—"}
          detail="Demo records only — not government verification"
        />
        <Summary
          icon="eye"
          title="Packaging"
          tone={obs.length ? "warn" : "neu"}
          value={
            a.packaging?.status === "compared" ? `${obs.length} observation${obs.length === 1 ? "" : "s"}` : label(a.packaging?.status)
          }
          detail="Observations only — not proof of counterfeiting"
        />
        <Summary
          icon="rules"
          title="Labelling rules"
          tone={failN ? "warn" : "ok"}
          value={`${failN} missing · ${claimN} claim${claimN === 1 ? "" : "s"}`}
          detail={`${a.compliance?.passed ?? 0} demo rules passed`}
        />
      </div>

      <div className="grid grid-cols-[minmax(0,1fr)_300px] gap-5 items-start max-[960px]:grid-cols-1">
        <div className="flex flex-col gap-5 min-w-0">
          <Panel
            title="Approved label information"
            action={<TextLink href={`/inspector/verify/${id}`}>Back to field verification</TextLink>}
          >
            <table className="cs-table">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Value</th>
                  <th>AI confidence</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {keyFields.map(
                  (k) =>
                    f[k] && (
                      <tr key={k}>
                        <td>
                          <strong>{f[k].label}</strong>
                        </td>
                        <td style={{ overflowWrap: "anywhere" }}>
                          <span className="cs-cell-label">Value</span>
                          {f[k].value ?? "Not present"}
                          {f[k].status === "edited" && (
                            <div style={{ fontSize: 12, color: "#55584E" }}>AI read: {f[k].ai_value ?? "—"}</div>
                          )}
                        </td>
                        <td>
                          <span className="cs-cell-label">AI confidence</span>
                          {f[k].confidence_level}
                          {f[k].source_photo ? ` · Photo ${f[k].source_photo}` : ""}
                        </td>
                        <td>
                          <Chip status={f[k].status === "auto" ? "confirmed" : f[k].status} />
                        </td>
                      </tr>
                    ),
                )}
              </tbody>
            </table>
          </Panel>

          {a.reference?.comparisons?.length ? (
            <Panel title="Reference comparison">
              <p className="mt-0" style={{ fontSize: 13.5, color: "#55584E" }}>
                {a.reference.detail}
              </p>
              <table className="cs-table">
                <thead>
                  <tr>
                    <th>Field</th>
                    <th>On pack</th>
                    <th>Demo reference</th>
                    <th>Result</th>
                  </tr>
                </thead>
                <tbody>
                  {a.reference.comparisons.map((r) => (
                    <tr key={r.field}>
                      <td>
                        <strong>{r.field}</strong>
                      </td>
                      <td>
                        <span className="cs-cell-label">On pack</span>
                        {r.extracted}
                      </td>
                      <td>
                        <span className="cs-cell-label">Demo reference</span>
                        {r.reference}
                      </td>
                      <td>
                        <Chip status={r.result} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mb-0" style={{ fontSize: 12.5, color: "#686B60" }}>
                Comparisons use fictional demonstration records. A match is not official government verification.
              </p>
            </Panel>
          ) : null}

          <Panel title="Packaging comparison">
            <p className="m-0" style={{ fontSize: 13.5, color: "#55584E" }}>
              {a.packaging?.summary || "No packaging comparison available."}
              {a.packaging?.version ? ` Reference version: ${a.packaging.version} (demo).` : ""}
            </p>
          </Panel>

          <section aria-label="Findings to review" className="flex flex-col gap-3.5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="cs-h2">Findings to review</h2>
              {open.length > 0 ? (
                <span className="flex items-center gap-1.5" style={{ fontSize: 13, fontWeight: 700, color: "#7A4808" }}>
                  <Icon name="alert" size={15} />
                  {open.length} finding{open.length > 1 ? "s" : ""} still open
                </span>
              ) : (
                <span style={{ fontSize: 13, fontWeight: 700, color: "#3B5420" }}>All findings reviewed</span>
              )}
            </div>
            {d.findings.length === 0 && (
              <Panel>
                <p className="m-0">No findings — every check passed against the demo data.</p>
              </Panel>
            )}
            {d.findings.map((x) => (
              <FindingCard key={`${x.id}-${x.decision?.action ?? ""}`} f={x} onDecide={(b) => decide(x.id, b)} />
            ))}
          </section>
        </div>

        <aside className="cs-panel flex flex-col gap-4 min-[961px]:sticky min-[961px]:top-6" aria-label="Your decision">
          <h2 className="cs-h2">Your decision</h2>
          {sug && (
            <div
              className="flex gap-2 rounded-[10px] border border-line p-3"
              style={{ background: "#FBF8F0", fontSize: 13, lineHeight: 1.5, color: "#55584E" }}
            >
              <Icon name="info" size={16} />
              <span>
                Suggested: <strong style={{ color: "#20231D" }}>{label(sug.classification)}</strong> — {sug.reasons.join("; ")}. Provisional
                criteria. The choice is yours.
              </span>
            </div>
          )}
          <fieldset className="m-0 p-0 border-0 flex flex-col gap-2.5">
            <legend className="cs-label mb-2">Final classification</legend>
            {CLASSES.map(([k, t, s]) => (
              <label
                key={k}
                className="flex gap-3 rounded-[10px] p-3 cursor-pointer"
                style={{ border: `1px solid ${choice === k ? "#56703A" : "#E5E4DA"}`, background: choice === k ? "#EEF2E1" : "#fff" }}
              >
                <input
                  type="radio"
                  name="classification"
                  value={k}
                  checked={choice === k}
                  onChange={() => {
                    setChoice(k);
                    setSaved(false);
                  }}
                  className="mt-1 accent-[#3E5228]"
                />
                <span>
                  <strong style={{ fontSize: 14.5 }}>{t}</strong>
                  <span className="block" style={{ fontSize: 12.5, color: "#55584E" }}>
                    {s}
                  </span>
                </span>
              </label>
            ))}
          </fieldset>
          <TextArea
            label="Remarks"
            value={remarks}
            onChange={(e) => {
              setRemarks(e.target.value);
              setSaved(false);
            }}
            maxLength={8000}
            placeholder="Observations, follow-up actions, samples taken…"
          />
          {open.length > 0 && (
            <span style={{ fontSize: 12.5, color: "#7A4808" }}>
              {open.length} finding{open.length > 1 ? "s are" : " is"} still open — you can still decide.
            </span>
          )}
          <div className="flex flex-col gap-2.5">
            <Button variant="secondary" disabled={!choice || d.analysis_stale} working={saving} onClick={() => void saveDecision(false)}>
              {saved ? "Decision saved" : "Save decision"}
            </Button>
            <Button iconRight="arrow" disabled={!choice || d.analysis_stale} onClick={() => void saveDecision(true)}>
              Continue to report
            </Button>
          </div>
        </aside>
      </div>
    </>
  );
}
