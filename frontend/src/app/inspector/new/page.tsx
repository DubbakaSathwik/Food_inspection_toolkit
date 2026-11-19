"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { Icon } from "@/components/icon";
import { CropDialog, Stepper } from "@/components/inspection";
import { AuthImage, useBlobUrl } from "@/components/media";
import { PageHeader } from "@/components/shell";
import { Backlink, Button, ErrorBox, Notice, Panel } from "@/components/ui";
import { api, errorMessage, type Inspection, type Photo } from "@/lib/api";

const CATEGORIES = [
  ["beverages", "Packaged Beverages & Water"],
  ["snacks", "Packaged Snacks"],
  ["dairy", "Dairy Products"],
  ["staples", "Groceries & Food Staples"],
] as const;
const LABELS = [
  ["front", "Front"],
  ["back", "Back"],
  ["side", "Side"],
  ["closeup", "Close-up"],
  ["other", "Other"],
] as const;
const labelName = (l: string) => LABELS.find(([k]) => k === l)?.[1] ?? "Photo";
const MAX = 5;

function NewInspectionInner() {
  const router = useRouter();
  const params = useSearchParams();
  const [insp, setInsp] = useState<Inspection | null>(null);
  const [selected, setSelected] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [category, setCategory] = useState<string | null>(null);
  const [cropOpen, setCropOpen] = useState(false);
  const [drag, setDrag] = useState(false);
  const replaceIdx = useRef<number | null>(null);
  const camera = useRef<HTMLInputElement>(null);
  const gallery = useRef<HTMLInputElement>(null);
  const id = params.get("id");

  useEffect(() => {
    if (!id) return;
    api<Inspection>(`/api/v1/inspections/${id}`)
      .then((d) => {
        if (d.status === "completed") router.replace(`/inspector/report/${d.id}`);
        setInsp(d);
        setCategory(d.category ?? null);
      })
      .catch((e) => setErr(errorMessage(e)));
  }, [id, router]);

  const ensure = useCallback(async (): Promise<Inspection> => {
    if (insp) return insp;
    const created = await api<Inspection>("/api/v1/inspections", { method: "POST" });
    setInsp(created);
    router.replace(`/inspector/new?id=${created.id}`);
    return created;
  }, [insp, router]);

  async function chooseCategory(c: string) {
    setCategory(c);
    try {
      const i = await ensure();
      setInsp(await api<Inspection>(`/api/v1/inspections/${i.id}/category`, { method: "PUT", body: { category: c } }));
    } catch (e) {
      setErr(errorMessage(e));
    }
  }

  async function upload(files: FileList | File[]) {
    setErr(null);
    const list = Array.from(files);
    if (!list.length) return;
    setBusy("upload");
    try {
      let current = await ensure();
      const replacing = replaceIdx.current;
      replaceIdx.current = null;
      if (replacing !== null && current.photos[replacing]) {
        const old = current.photos[replacing];
        current = await api<Inspection>(`/api/v1/inspections/${current.id}/photos/${old.id}`, { method: "DELETE" });
      }
      for (const f of list) {
        if (current.photos.length >= MAX) {
          setErr(`An inspection can have up to ${MAX} photographs.`);
          break;
        }
        const form = new FormData();
        form.append("file", f);
        form.append("label", (["front", "back", "side", "closeup", "other"] as const)[Math.min(current.photos.length, 4)]);
        current = await api<Inspection>(`/api/v1/inspections/${current.id}/photos`, { method: "POST", form });
      }
      setInsp(current);
      setSelected(Math.max(0, current.photos.length - 1));
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(null);
    }
  }

  async function patchPhoto(p: Photo, body: Record<string, unknown>) {
    if (!insp) return;
    try {
      setInsp(await api<Inspection>(`/api/v1/inspections/${insp.id}/photos/${p.id}`, { method: "PATCH", body }));
    } catch (e) {
      setErr(errorMessage(e));
    }
  }

  async function remove(p: Photo) {
    if (!insp) return;
    setBusy("remove");
    try {
      const d = await api<Inspection>(`/api/v1/inspections/${insp.id}/photos/${p.id}`, { method: "DELETE" });
      setInsp(d);
      setSelected((s) => Math.max(0, Math.min(s, d.photos.length - 1)));
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(null);
    }
  }

  const photos = insp?.photos ?? [];
  const sel = photos[selected];
  const issues = photos.map((p, i) => ({ p, i })).filter(({ p }) => !p.quality.ok);
  const cropSrc = useBlobUrl(cropOpen && insp && sel ? `/api/v1/inspections/${insp.id}/photos/${sel.id}` : null).url;
  const okList = photos.map((p, i) => (p.quality.ok ? i + 1 : null)).filter(Boolean);

  return (
    <>
      <PageHeader
        title="New Inspection"
        subtitle="Add photographs of one packaged food product. Up to five images."
        back={<Backlink href="/inspector">Back to dashboard</Backlink>}
      />
      <Stepper current={1} />
      {err && <ErrorBox error={err} />}

      <Panel>
        <h2 className="cs-h2">Product category</h2>
        <p className="mt-1.5 mb-4" style={{ fontSize: 14, color: "#55584E" }}>
          Selects which labelling rules are applied.{" "}
          {category ? (
            <>
              Currently selected: <strong style={{ color: "#20231D" }}>{CATEGORIES.find(([k]) => k === category)?.[1]}</strong>
            </>
          ) : (
            "If you skip this, the AI suggests one and you can change it."
          )}
        </p>
        <div role="radiogroup" aria-label="Product category" className="grid grid-cols-4 gap-3 max-[960px]:grid-cols-2 cs-grid-1">
          {CATEGORIES.map(([k, l]) => {
            const on = category === k;
            return (
              <button
                key={k}
                type="button"
                role="radio"
                aria-checked={on}
                onClick={() => void chooseCategory(k)}
                className="flex items-center gap-3 rounded-[10px] px-4 text-left min-h-[50px] cursor-pointer"
                style={{
                  border: `1px solid ${on ? "#56703A" : "#D8D6C9"}`,
                  background: on ? "#EEF2E1" : "#fff",
                  fontSize: 14.5,
                  fontWeight: on ? 700 : 500,
                  color: "#20231D",
                }}
              >
                <span
                  aria-hidden
                  className="grid place-items-center shrink-0"
                  style={{ width: 18, height: 18, borderRadius: 9, border: `1.5px solid ${on ? "#3E5228" : "#9a9c92"}` }}
                >
                  {on && <span style={{ width: 9, height: 9, borderRadius: 5, background: "#3E5228" }} />}
                </span>
                {l}
              </button>
            );
          })}
        </div>
      </Panel>

      <div className="grid grid-cols-[minmax(0,1fr)_280px] gap-5 items-start max-[960px]:grid-cols-1">
        <Panel>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="cs-h2">Product photographs</h2>
              <p className="m-0 mt-1" style={{ fontSize: 13.5, color: "#55584E" }}>
                {photos.length} of {MAX} added
              </p>
            </div>
            <div className="flex flex-wrap gap-2.5 cs-acts">
              <Button
                variant="secondary"
                small
                icon="camera"
                onClick={() => camera.current?.click()}
                disabled={photos.length >= MAX || !!busy}
              >
                Take photo
              </Button>
              <Button
                variant="secondary"
                small
                icon="upload"
                onClick={() => gallery.current?.click()}
                disabled={photos.length >= MAX || !!busy}
              >
                Choose from gallery
              </Button>
            </div>
          </div>
          <input
            ref={camera}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            capture="environment"
            hidden
            onChange={(e) => {
              if (e.target.files) void upload(e.target.files);
              e.target.value = "";
            }}
          />
          <input
            ref={gallery}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            hidden
            onChange={(e) => {
              if (e.target.files) void upload(e.target.files);
              e.target.value = "";
            }}
          />

          <div
            className={`mt-4 flex items-center justify-center gap-2.5 rounded-[10px] px-4 py-5 text-center ${busy === "upload" ? "cs-working" : ""}`}
            style={{
              border: `1.5px dashed ${drag ? "#56703A" : "#C9C6B4"}`,
              background: drag ? "#EEF2E1" : "#FBF8F0",
              fontSize: 13.5,
              color: "#55584E",
            }}
            onDragOver={(e) => {
              e.preventDefault();
              setDrag(true);
            }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDrag(false);
              void upload(e.dataTransfer.files);
            }}
          >
            <Icon name="upload" size={18} />
            <span>
              <strong style={{ color: "#20231D" }}>{busy === "upload" ? "Uploading" : "Drop images here"}</strong> or use the buttons above
              · JPG, PNG or WebP, up to 12 MB each
            </span>
          </div>

          {issues.length > 0 && (
            <div
              className="mt-4 flex gap-2.5 rounded-[10px] px-4 py-3"
              role="status"
              style={{ background: "#FBEFD9", border: "1px solid #EBCF9E", color: "#7A4808", fontSize: 13.5, lineHeight: 1.55 }}
            >
              <Icon name="alert" size={17} />
              <span>
                {issues.map(({ p, i }) => (
                  <span key={p.id} className="block">
                    <strong>
                      Issue found in Photo {i + 1} ({labelName(p.label)}).
                    </strong>{" "}
                    {p.quality.issues.join(" ")} Retake it or continue anyway.
                  </span>
                ))}
                {okList.length > 0 && (
                  <span>
                    Photos {okList.join(", ")} {okList.length === 1 ? "is" : "are"} fine.
                  </span>
                )}
              </span>
            </div>
          )}

          <div className="cs-strip mt-4" role="listbox" aria-label="Photographs">
            {Array.from({ length: MAX }, (_, i) => {
              const p = photos[i];
              const on = i === selected && !!p;
              const tone = !p ? "empty" : p.quality.ok ? "ok" : "bad";
              const border = tone === "ok" ? "#56703A" : tone === "bad" ? "#C9893A" : "#C9C6B4";
              return (
                <button
                  key={i}
                  type="button"
                  role="option"
                  aria-selected={on}
                  disabled={!p}
                  onClick={() => p && setSelected(i)}
                  className="flex flex-col items-center gap-1.5 rounded-[10px] p-2 cursor-pointer disabled:cursor-default"
                  style={{ width: 92, border: `${on ? 2.5 : 1.5}px ${p ? "solid" : "dashed"} ${border}`, background: "#fff" }}
                >
                  <span
                    className="grid place-items-center overflow-hidden rounded-[6px]"
                    style={{ width: 74, height: 64, background: "#E8E5DA", color: "#9CAB84", fontSize: 20, fontWeight: 700 }}
                  >
                    {p && insp ? (
                      <AuthImage
                        path={`/api/v1/inspections/${insp.id}/photos/${p.id}?thumb=true`}
                        alt={`Photo ${i + 1}`}
                        style={{ objectFit: "cover" }}
                      />
                    ) : (
                      i + 1
                    )}
                  </span>
                  <span style={{ fontSize: 11.5, fontWeight: 700, color: "#20231D", whiteSpace: "nowrap" }}>
                    Photo {i + 1} · {p ? labelName(p.label) : "Empty"}
                  </span>
                  <span
                    className={`cs-chip ${tone === "ok" ? "tone-ok" : tone === "bad" ? "tone-warn" : "tone-neu"}`}
                    style={{ padding: "2px 6px", fontSize: 10.5 }}
                  >
                    {tone === "ok" ? "All okay" : tone === "bad" ? "Check" : "Empty"}
                  </span>
                </button>
              );
            })}
          </div>

          {sel && insp ? (
            <div
              className="mt-4 rounded-[12px] p-4 flex flex-col gap-3"
              style={{ border: `2px solid ${sel.quality.ok ? "#56703A" : "#C9893A"}`, background: sel.quality.ok ? "#EEF2E1" : "#FBF3E6" }}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <strong style={{ fontSize: 14 }}>
                  Photo {selected + 1} · {labelName(sel.label)}
                </strong>
                <div className="flex items-center gap-2">
                  <label className="sr-only" htmlFor="photo-label">
                    Photo side
                  </label>
                  <select
                    id="photo-label"
                    className="cs-select"
                    style={{ minHeight: 34, padding: "4px 8px", width: "auto", fontSize: 13 }}
                    value={sel.label}
                    onChange={(e) => void patchPhoto(sel, { label: e.target.value })}
                  >
                    {LABELS.map(([k, l]) => (
                      <option key={k} value={k}>
                        {l}
                      </option>
                    ))}
                  </select>
                  <span className={`cs-chip ${sel.quality.ok ? "tone-ok" : "tone-warn"}`} style={{ background: "#fff" }}>
                    {sel.quality.ok ? "All okay" : "Quality warning"}
                  </span>
                </div>
              </div>
              <div className="rounded-[8px] overflow-hidden grid place-items-center" style={{ background: "#E8E5DA", height: 300 }}>
                <AuthImage path={`/api/v1/inspections/${insp.id}/photos/${sel.id}`} alt={`Photo ${selected + 1} preview`} />
              </div>
              <p className="m-0" style={{ fontSize: 13.5, color: sel.quality.ok ? "#3B5420" : "#7A4808" }}>
                {sel.quality.ok ? "Clear and readable. No problems found." : sel.quality.issues.join(" ")}
                {sel.crop ? " · Cropped area will be used for analysis." : ""}
              </p>
              <div className="grid grid-cols-3 gap-2.5 cs-acts">
                <Button variant="secondary" small icon="crop" onClick={() => setCropOpen(true)}>
                  Crop
                </Button>
                <Button
                  variant="secondary"
                  small
                  icon="refresh"
                  onClick={() => {
                    replaceIdx.current = selected;
                    gallery.current?.click();
                  }}
                >
                  Replace
                </Button>
                <Button variant="secondary" small icon="trash" working={busy === "remove"} onClick={() => void remove(sel)}>
                  Remove
                </Button>
              </div>
            </div>
          ) : (
            <div className="mt-4">
              <Notice>Add at least one photograph — the front of the pack is a good start.</Notice>
            </div>
          )}
          <p className="mt-4 mb-0 flex gap-2" style={{ fontSize: 12.5, color: "#686B60" }}>
            <Icon name="info" size={15} />
            Original photographs are kept unchanged as evidence and embedded in the report. Cropped copies are used only for analysis.
          </p>
        </Panel>

        <aside className="cs-panel" aria-label="Capture guidance">
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, lineHeight: 1.3 }}>For better results — cover these areas</h2>
          <ul
            className="mt-3 mb-4 pl-4 flex flex-col gap-2.5 list-disc marker:text-[#9CAB84]"
            style={{ fontSize: 13.5, color: "#55584E", lineHeight: 1.5 }}
          >
            <li>Front of pack — product name and brand</li>
            <li>Back — ingredients and nutrition</li>
            <li>Manufacturer address and licence number</li>
            <li>Batch, manufacturing and expiry dates</li>
            <li>MRP, net quantity and customer-care details</li>
          </ul>
          <p className="m-0 pt-3 border-t border-line" style={{ fontSize: 13, color: "#55584E", lineHeight: 1.55 }}>
            Hold the camera parallel to the label, avoid glare, and fill the frame with the text you need.
          </p>
        </aside>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 cs-bar">
        <Button variant="secondary" disabled={!insp} onClick={() => router.push("/inspector")}>
          Save draft
        </Button>
        <div className="flex flex-wrap items-center gap-3 cs-bar">
          {issues.length > 0 && (
            <span style={{ fontSize: 13, color: "#55584E" }}>
              {issues.length} image{issues.length > 1 ? "s have" : " has"} a quality warning
            </span>
          )}
          <Button
            iconRight="arrow"
            disabled={!insp || photos.length === 0}
            onClick={() => insp && router.push(`/inspector/verify/${insp.id}?run=1`)}
          >
            Extract Label Information
          </Button>
        </div>
      </div>

      <CropDialog
        open={cropOpen}
        src={cropSrc}
        initial={sel?.crop ?? null}
        onClose={() => setCropOpen(false)}
        onSave={(r) => {
          if (sel) void patchPhoto(sel, { crop: r });
          setCropOpen(false);
        }}
        onClear={() => {
          if (sel) void patchPhoto(sel, { clear_crop: true });
          setCropOpen(false);
        }}
      />
    </>
  );
}

export default function NewInspectionPage() {
  return (
    <Suspense fallback={null}>
      <NewInspectionInner />
    </Suspense>
  );
}
