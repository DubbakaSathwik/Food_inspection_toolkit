"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { Icon } from "@/components/icon";
import { AIWorkingOverlay, Stepper } from "@/components/inspection";
import { AuthImage } from "@/components/media";
import { PageHeader } from "@/components/shell";
import { Backlink, Button, Chip, ErrorBox, LoadingBlock, Modal, Notice, Panel, Pill, SelectField } from "@/components/ui";
import { api, errorMessage, type Field, type Inspection } from "@/lib/api";

const READ_STEPS = [
  "Preparing photographs",
  "Reading label text",
  "Structuring product fields",
  "Checking dates, numbers and licence format",
];

function FieldCard({
  f,
  busy,
  onSave,
  onConfirm,
}: {
  f: Field;
  busy: boolean;
  onSave: (v: string | null) => Promise<void>;
  onConfirm: () => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(f.value ?? "");
  const done = f.status !== "pending";
  const auto = f.status === "auto";
  const long = (f.value ?? "").length > 80 || ["ingredients", "nutrition", "other_text", "manufacturer_address"].includes(f.key);
  return (
    <article
      className="rounded-[10px] p-4 flex flex-col gap-2.5"
      aria-label={f.label}
      style={{
        border: `1px solid ${done ? "#9CAB84" : "#E5E4DA"}`,
        borderLeft: `4px solid ${done ? "#56703A" : "#D8D6C9"}`,
        background: done ? "#FBF8F0" : "#fff",
      }}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <span className="flex items-center gap-2" style={{ fontSize: 14, fontWeight: 700 }}>
          <span aria-hidden style={{ width: 7, height: 7, borderRadius: 4, background: done ? "#56703A" : "#C9C6B4" }} />
          {f.label}
        </span>
        <span className="flex flex-wrap items-center gap-2" style={{ fontSize: 12.5, color: "#686B60" }}>
          {f.flag === "check" && (
            <Chip tone="warn" dot={false}>
              Looks unusual
            </Chip>
          )}
          {f.flag === "not_found" && (
            <Chip tone="neu" dot={false}>
              Not found
            </Chip>
          )}
          <span style={{ color: f.confidence_level === "Low" ? "#7A4808" : undefined, fontWeight: 600 }}>
            AI confidence: {f.confidence_level}
          </span>
          <span>{f.source_photo ? `Photo ${f.source_photo}` : "—"}</span>
          {!done && (
            <Chip tone="neu" dot={false}>
              Needs check
            </Chip>
          )}
        </span>
      </div>
      {auto && (
        <span>
          <Chip tone="ok" dot={false}>
            Auto-confirmed (high confidence)
          </Chip>
        </span>
      )}
      {f.status === "edited" && (
        <span>
          <Chip tone="info" dot={false}>
            Corrected by you
          </Chip>
        </span>
      )}
      {f.status === "confirmed" && (
        <span>
          <Chip tone="ok" dot={false}>
            Confirmed by you
          </Chip>
        </span>
      )}
      {editing ? (
        <div className="flex flex-col gap-2">
          <label className="sr-only" htmlFor={`v-${f.key}`}>
            {f.label}
          </label>
          {long ? (
            <textarea id={`v-${f.key}`} className="cs-textarea" value={draft} onChange={(e) => setDraft(e.target.value)} maxLength={4000} />
          ) : (
            <input
              id={`v-${f.key}`}
              className="cs-input"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              maxLength={4000}
              autoFocus
            />
          )}
          <div className="flex flex-wrap gap-2 cs-acts">
            <Button
              small
              working={busy}
              onClick={async () => {
                await onSave(draft.trim() || null);
                setEditing(false);
              }}
            >
              Save
            </Button>
            <Button
              small
              variant="secondary"
              onClick={() => {
                setDraft(f.value ?? "");
                setEditing(false);
              }}
            >
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <p className="m-0" style={{ fontSize: 14.5, lineHeight: 1.5, overflowWrap: "anywhere", color: f.value ? "#20231D" : "#686B60" }}>
          {f.value ?? "Not found on photographs"}
        </p>
      )}
      {f.note && (
        <p className="m-0" style={{ fontSize: 12.5, color: f.flag === "check" ? "#7A4808" : "#686B60" }}>
          {f.note}
        </p>
      )}
      {f.status === "edited" && (
        <p className="m-0" style={{ fontSize: 12.5, color: "#55584E" }}>
          Original AI value (kept for the report): <strong>{f.ai_value ?? "not found"}</strong>
        </p>
      )}
      {!editing && (
        <div className="flex flex-wrap gap-2 cs-acts">
          {!done && (
            <Button small icon="tick" working={busy} onClick={() => void onConfirm()}>
              Correct
            </Button>
          )}
          <Button
            small
            variant="secondary"
            icon="edit"
            onClick={() => {
              setDraft(f.value ?? "");
              setEditing(true);
            }}
          >
            {done ? "Edit" : "Fix value"}
          </Button>
          {!done && (
            <Button small variant="secondary" icon="flag" onClick={() => void onSave(null)}>
              Not on pack
            </Button>
          )}
          {f.status === "edited" && (
            <Button small variant="secondary" icon="refresh" onClick={() => void onSave(f.ai_value ?? null)}>
              Restore AI value
            </Button>
          )}
        </div>
      )}
    </article>
  );
}

export default function VerifyFieldsPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [d, setD] = useState<Inspection | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [reading, setReading] = useState(false);
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [viewPhoto, setViewPhoto] = useState<number | null>(null);
  const started = useRef(false);

  const extract = useCallback(async () => {
    setErr(null);
    setReading(true);
    try {
      setD(await api<Inspection>(`/api/v1/inspections/${id}/extract`, { method: "POST" }));
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setReading(false);
    }
  }, [id]);

  useEffect(() => {
    api<Inspection>(`/api/v1/inspections/${id}`)
      .then((x) => {
        setD(x);
        if (x.status === "completed") router.replace(`/inspector/report/${id}`);
        const run = new URLSearchParams(window.location.search).get("run") === "1";
        if (!started.current && x.photos.length > 0 && (x.status === "draft" || (run && x.extraction.status !== "done"))) {
          started.current = true;
          void extract();
        }
      })
      .catch((e) => setErr(errorMessage(e)));
  }, [id, router, extract]);

  async function save(key: string, value: string | null) {
    setBusyKey(key);
    try {
      setD(await api<Inspection>(`/api/v1/inspections/${id}/fields/${key}`, { method: "PATCH", body: { value, confirm: true } }));
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusyKey(null);
    }
  }
  async function confirm(keys: string[]) {
    setBusyKey(keys.length === 1 ? keys[0] : "all");
    try {
      setD(await api<Inspection>(`/api/v1/inspections/${id}/fields/confirm`, { method: "POST", body: { keys } }));
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusyKey(null);
    }
  }
  async function setCategory(category: string) {
    try {
      setD(await api<Inspection>(`/api/v1/inspections/${id}/category`, { method: "PUT", body: { category } }));
    } catch (e) {
      setErr(errorMessage(e));
    }
  }

  const fields = d?.fields ?? [];
  const groups = fields.reduce<Record<string, Field[]>>((acc, f) => ((acc[f.group] ??= []).push(f), acc), {});
  const autoN = fields.filter((f) => f.status === "auto").length;
  const pendingN = fields.filter((f) => f.status === "pending").length;
  const checked = fields.length - pendingN;
  const failed = d?.extraction.status === "failed" || d?.status === "incomplete";
  const title = d
    ? [d.id, fields.find((f) => f.key === "product_name")?.value, `${d.photos.length} photograph${d.photos.length === 1 ? "" : "s"}`]
        .filter(Boolean)
        .join(" · ")
    : "";

  return (
    <>
      <AIWorkingOverlay title="AI is reading the label" steps={READ_STEPS} active={reading} interval={1400} />
      <PageHeader
        title="Verify Extracted Information"
        subtitle={title}
        back={<Backlink href={`/inspector/new?id=${id}`}>Back to photographs</Backlink>}
        actions={<Pill>Step 2 of 5</Pill>}
      />
      <Stepper current={2} />
      {err && <ErrorBox error={err} />}
      {!d ? (
        <Panel>
          <LoadingBlock />
        </Panel>
      ) : failed && !reading ? (
        <Panel title="The AI could not read the label">
          <p className="mt-0" style={{ fontSize: 14.5, color: "#55584E" }}>
            Your photographs are saved. The inspection is marked incomplete — you can retry now or later from the dashboard.
          </p>
          <ul className="mb-4" style={{ fontSize: 13, color: "#686B60" }}>
            {d.extraction.attempts.slice(-4).map((a, i) => (
              <li key={i}>
                {a.provider}: {a.ok ? "ok" : a.error}
              </li>
            ))}
          </ul>
          <div className="flex flex-wrap gap-3 cs-acts">
            <Button icon="refresh" onClick={() => void extract()}>
              Retry AI reading
            </Button>
            <Button variant="secondary" onClick={() => router.push(`/inspector/new?id=${id}`)}>
              Change photographs
            </Button>
          </div>
        </Panel>
      ) : fields.length === 0 ? (
        <Panel>
          <Notice>Waiting for the AI reading to start…</Notice>
          <div className="mt-3">
            <Button onClick={() => void extract()}>Read label now</Button>
          </div>
        </Panel>
      ) : (
        <>
          <Panel>
            <h2 className="cs-h2">Check what was read from the label</h2>
            <p className="mt-1.5 mb-4" style={{ fontSize: 14, color: "#55584E", lineHeight: 1.55, maxWidth: 640 }}>
              Fields the AI read with high confidence, and that pass format checks, are confirmed automatically. Only the uncertain ones are
              left for you. Every field can still be edited.
            </p>
            <div className="flex flex-wrap items-end gap-3 mb-4 cs-acts">
              <Button variant="secondary" icon="check" disabled={!pendingN} working={busyKey === "all"} onClick={() => void confirm([])}>
                Confirm all remaining
              </Button>
              <Button variant="secondary" icon="refresh" onClick={() => void extract()}>
                Replay AI reading
              </Button>
              <SelectField
                label="Product category"
                value={d.category ?? ""}
                onChange={(e) => void setCategory(e.target.value)}
                className="min-w-[220px]"
              >
                <option value="" disabled>
                  Choose category
                </option>
                <option value="beverages">Packaged beverages & water</option>
                <option value="snacks">Packaged snacks</option>
                <option value="dairy">Dairy products</option>
                <option value="staples">Groceries & food staples</option>
              </SelectField>
            </div>
            <div
              className="flex flex-wrap items-center gap-2 rounded-[10px] px-4 py-3"
              style={{ background: "#EEF2E1", fontSize: 13.5, fontWeight: 600, color: "#3B5420" }}
            >
              <Icon name="check" size={16} /> {autoN} high-confidence fields were confirmed automatically
              {pendingN > 0 && <span style={{ color: "#7A4808" }}>· {pendingN} need your check</span>}
              {d.extraction.provider && (
                <span style={{ color: "#686B60", fontWeight: 500 }}>
                  · read by {d.extraction.provider}
                  {d.extraction.ocr_used ? " (OCR fallback)" : ""}
                </span>
              )}
            </div>
            <div className="mt-4 flex items-center gap-4">
              <div
                className="flex-1 h-2 rounded-full"
                style={{ background: "#EEF2E1" }}
                role="progressbar"
                aria-valuenow={checked}
                aria-valuemax={fields.length}
                aria-label="Fields checked"
              >
                <div
                  className="h-2 rounded-full"
                  style={{ width: `${(checked / Math.max(fields.length, 1)) * 100}%`, background: "#56703A", transition: "width .3s" }}
                />
              </div>
              <strong style={{ fontSize: 14, whiteSpace: "nowrap" }}>
                {checked} of {fields.length} fields checked
              </strong>
            </div>
          </Panel>

          <div className="grid grid-cols-[minmax(0,1fr)_280px] gap-5 items-start max-[960px]:grid-cols-1">
            <div className="flex flex-col gap-5 min-w-0">
              {Object.entries(groups).map(([g, list]) => (
                <Panel key={g}>
                  <h2 className="flex items-baseline gap-2 mb-3.5" style={{ fontSize: 16, fontWeight: 700, margin: "0 0 14px" }}>
                    {g} <span style={{ fontSize: 12, fontWeight: 600, color: "#686B60" }}>{list.length} fields</span>
                  </h2>
                  <div className="flex flex-col gap-3">
                    {list.map((f) => (
                      <FieldCard
                        key={`${f.key}-${f.status}-${f.value}`}
                        f={f}
                        busy={busyKey === f.key}
                        onSave={(v) => save(f.key, v)}
                        onConfirm={() => confirm([f.key])}
                      />
                    ))}
                  </div>
                </Panel>
              ))}
            </div>
            <div className="flex flex-col gap-5">
              <aside className="cs-panel" aria-label="Photographs">
                <h2 style={{ margin: "0 0 12px", fontSize: 16, fontWeight: 700 }}>Photographs</h2>
                <div className="grid grid-cols-3 gap-2">
                  {d.photos.map((p, i) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => setViewPhoto(i)}
                      className="flex flex-col items-center gap-1 rounded-[8px] border border-line p-1.5 bg-white cursor-pointer"
                      aria-label={`Open photo ${i + 1}`}
                    >
                      <span className="block w-full overflow-hidden rounded-[6px]" style={{ height: 64, background: "#E8E5DA" }}>
                        <AuthImage
                          path={d.photos_deleted ? null : `/api/v1/inspections/${id}/photos/${p.id}?thumb=true`}
                          alt={`Photo ${i + 1}`}
                          style={{ objectFit: "cover" }}
                        />
                      </span>
                      <span style={{ fontSize: 11, fontWeight: 600 }}>Photo {i + 1}</span>
                    </button>
                  ))}
                </div>
                <p className="mb-0" style={{ fontSize: 12.5, color: "#55584E" }}>
                  Open a photograph to compare it with the value you are checking.
                </p>
              </aside>
              <aside className="cs-panel" aria-label="What happens next">
                <h2 style={{ margin: "0 0 10px", fontSize: 16, fontWeight: 700 }}>What happens next</h2>
                <ol className="m-0 pl-5 flex flex-col gap-2 list-decimal" style={{ fontSize: 13.5, color: "#55584E", lineHeight: 1.5 }}>
                  <li>Your approved values go to the AI review.</li>
                  <li>Reference, licence, packaging and labelling checks run against them.</li>
                  <li>You review the findings and record the final decision.</li>
                </ol>
                <p className="mb-0" style={{ fontSize: 12.5, color: "#686B60" }}>
                  Original AI values and your corrections are both kept and shown in the report.
                </p>
              </aside>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 cs-bar">
            <Button variant="secondary" onClick={() => router.push("/inspector")}>
              Save and exit
            </Button>
            <div className="flex flex-wrap items-center gap-3 cs-bar">
              {(pendingN > 0 || !d.category) && (
                <span style={{ fontSize: 13, color: "#55584E" }}>
                  {pendingN > 0 ? `${pendingN} field${pendingN > 1 ? "s" : ""} still need your check` : "Choose the product category"}
                </span>
              )}
              <Button iconRight="arrow" disabled={pendingN > 0 || !d.category} onClick={() => router.push(`/inspector/ai-review/${id}`)}>
                Continue to AI Review
              </Button>
            </div>
          </div>
        </>
      )}
      <Modal open={viewPhoto !== null} title={viewPhoto !== null ? `Photo ${viewPhoto + 1}` : ""} onClose={() => setViewPhoto(null)} wide>
        {viewPhoto !== null && d && (
          <div style={{ height: "60vh" }}>
            <AuthImage path={`/api/v1/inspections/${id}/photos/${d.photos[viewPhoto].id}`} alt={`Photo ${viewPhoto + 1}`} />
          </div>
        )}
      </Modal>
    </>
  );
}
