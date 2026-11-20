"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Icon, type IconName } from "@/components/icon";
import { ImageSlot, refreshSiteImages } from "@/components/media";
import { ProfileView } from "@/components/profile-view";
import { PageHeader } from "@/components/shell";
import { Button, Chip, ErrorBox, fmtDate, LoadingBlock, Notice, Panel, TextArea, TextField } from "@/components/ui";
import { ApiError, api, errorMessage, type SettingsOut } from "@/lib/api";

const TABS = [
  ["images", "Website Images"],
  ["general", "General"],
  ["ai", "AI & OCR"],
  ["limits", "Limits & Usage"],
  ["account", "My account"],
] as const;
type Tab = (typeof TABS)[number][0];
/** [key, title, where it appears, recommended size, tip]. RATIO is the shape of the box on the live page (the image is cropped to fill it). */
const SLOTS = [
  [
    "hero",
    "Landing page hero",
    "Public landing page, beside the main heading.",
    "1200 × 1050 px (8:7)",
    "Clean product photograph on a neutral surface. Keep the subject in the middle; the edges may be cropped.",
  ],
  [
    "signin",
    "Sign-in panel",
    "Left panel of the sign-in and awaiting-approval screens.",
    "1200 × 1200 px (1:1, square)",
    "Square works best. On phones this panel becomes a wide strip, so keep the subject in the centre.",
  ],
  [
    "banner",
    "Inspector dashboard banner",
    'Beside "Start a New Inspection" on the inspector dashboard.',
    "1600 × 600 px (8:3, wide)",
    "Wide landscape. The sides are cropped on narrow screens, so keep the subject in the middle.",
  ],
] as const;
const RATIO: Record<string, number> = { hero: 8 / 7, signin: 1, banner: 8 / 3 };

export default function SettingsPage() {
  const [tab, setTab] = useState<Tab>("images");
  const [s, setS] = useState<SettingsOut | null>(null);
  const [draft, setDraft] = useState<SettingsOut | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [fieldErr, setFieldErr] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [imgV, setImgV] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const target = useRef<string>("hero");

  useEffect(() => {
    api<SettingsOut>("/api/v1/admin/settings")
      .then((x) => {
        setS(x);
        setDraft(x);
      })
      .catch((e) => setErr(errorMessage(e)));
  }, []);

  async function upload(f: File) {
    setBusy(target.current);
    setErr(null);
    try {
      const fd = new FormData();
      fd.append("file", f);
      const x = await api<SettingsOut>(`/api/v1/admin/settings/images/${target.current}`, { method: "PUT", form: fd });
      setS(x);
      setDraft((d) => d && { ...d, images: x.images });
      refreshSiteImages();
      setImgV((v) => v + 1);
      setNote("Image uploaded. It is now shown on the site.");
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(null);
    }
  }
  async function reset(key: string) {
    setBusy(key);
    try {
      const x = await api<SettingsOut>(`/api/v1/admin/settings/images/${key}`, { method: "DELETE" });
      setS(x);
      setDraft((d) => d && { ...d, images: x.images });
      refreshSiteImages();
      setImgV((v) => v + 1);
      setNote("Reset to the labelled placeholder.");
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(null);
    }
  }
  async function save() {
    if (!draft) return;
    setBusy("save");
    setErr(null);
    setFieldErr({});
    try {
      const x = await api<SettingsOut>("/api/v1/admin/settings", {
        method: "PATCH",
        body: { general: draft.general, ai: draft.ai, limits: draft.limits },
      });
      setS(x);
      setDraft(x);
      setNote("Settings saved and written to the audit log.");
    } catch (e) {
      if (e instanceof ApiError && e.fields) setFieldErr(e.fields);
      setErr(errorMessage(e));
    } finally {
      setBusy(null);
    }
  }
  const dirty = JSON.stringify([s?.general, s?.ai, s?.limits]) !== JSON.stringify([draft?.general, draft?.ai, draft?.limits]);

  return (
    <>
      <PageHeader title="Settings" subtitle="Site images, platform options, AI providers and usage limits." />
      <nav className="flex flex-wrap gap-2" role="tablist" aria-label="Settings sections">
        {TABS.map(([k, l]) => (
          <button
            key={k}
            type="button"
            role="tab"
            aria-selected={tab === k}
            onClick={() => {
              setTab(k);
              setNote(null);
            }}
            className="cs-btn2 cs-btn-sm"
            style={tab === k ? { background: "#E3EACF", borderColor: "#56703A", fontWeight: 700 } : undefined}
          >
            {l}
          </button>
        ))}
      </nav>
      <section className="cs-panel flex flex-col gap-3 min-[761px]:hidden" aria-label="More admin pages">
        <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>More</h2>
        {(
          [
            ["/admin/rules", "rules", "Compliance Rules"],
            ["/admin/proposals", "proposal", "Product Proposals"],
            ["/admin/audit", "logs", "Audit Logs"],
            ["/admin/diagnostics", "check", "System Diagnostics"],
          ] as [string, IconName, string][]
        ).map(([h, i, l]) => (
          <Link
            key={h}
            href={h}
            className="flex items-center gap-3 rounded-[10px] border border-line px-4 no-underline"
            style={{ minHeight: 50, color: "#20231D", fontWeight: 600 }}
          >
            <Icon name={i} />
            {l}
            <span className="ml-auto">
              <Icon name="chev" size={15} />
            </span>
          </Link>
        ))}
      </section>
      {note && (
        <Notice tone="ok" icon="check">
          {note}
        </Notice>
      )}
      {err && <ErrorBox error={err} />}
      {tab === "account" ? (
        <ProfileView showActivity={false} />
      ) : !draft ? (
        <Panel>
          <LoadingBlock rows={6} />
        </Panel>
      ) : (
        <Panel>
          {tab === "images" && (
            <>
              <h2 className="cs-h2">Website Images</h2>
              <p style={{ fontSize: 14, color: "#55584E", maxWidth: 640 }}>
                Upload the pictures used on the landing, sign-in and dashboard pages. Until you upload your own, each slot shows a labelled
                placeholder. Product photographs inside inspections come from inspectors and are not managed here.
              </p>
              <div className="flex flex-col gap-3.5">
                {SLOTS.map(([k, t, where, size, tip]) => {
                  const info = draft.images[k];
                  return (
                    <div key={k} className="flex flex-wrap gap-4 rounded-[12px] border border-line p-4" style={{ background: "#FBF8F0" }}>
                      <ImageSlot
                        key={`${k}-${imgV}`}
                        slot={k}
                        label={info ? t : "Current: placeholder"}
                        className="w-[200px] self-start max-[760px]:w-full"
                        style={{ aspectRatio: String(RATIO[k]) }}
                      />
                      <div className="flex-1 min-w-[220px] flex flex-col gap-1.5">
                        <strong>{t}</strong>
                        <span style={{ fontSize: 13.5, color: "#55584E" }}>{where}</span>
                        <span style={{ fontSize: 13, fontWeight: 700, color: "#20231D" }}>Use an image of {size}</span>
                        <span style={{ fontSize: 12.5, color: "#686B60" }}>
                          JPG, PNG or WebP · up to 5 MB · the box on the left shows the exact shape
                        </span>
                        <span style={{ fontSize: 12.5, color: "#686B60" }}>{tip}</span>
                        <span style={{ fontSize: 12.5, fontWeight: 700, color: "#56703A" }}>
                          {info ? `Custom image (${String(info.width)}×${String(info.height)})` : "Showing the labelled placeholder"}
                        </span>
                        {info && Math.abs(Number(info.width) / Number(info.height) / RATIO[k] - 1) > 0.25 && (
                          <span style={{ fontSize: 12.5, color: "#7A4808" }}>
                            This image has a different shape from the box, so it will be cropped to fit. Use {size} to control what is
                            visible.
                          </span>
                        )}
                        <div className="flex flex-wrap gap-2.5 mt-1 cs-acts">
                          <Button
                            small
                            icon="upload"
                            working={busy === k}
                            onClick={() => {
                              target.current = k;
                              input.current?.click();
                            }}
                          >
                            {info ? "Replace image" : "Upload image"}
                          </Button>
                          <Button small variant="secondary" disabled={!info} onClick={() => void reset(k)}>
                            Reset to placeholder
                          </Button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
              <input
                ref={input}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                hidden
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) void upload(f);
                  e.target.value = "";
                }}
              />
            </>
          )}
          {tab === "general" && (
            <div className="flex flex-col gap-4 max-w-[640px]">
              <h2 className="cs-h2">General</h2>
              <TextField
                label="Organisation name (report header)"
                value={draft.general.org_name}
                maxLength={200}
                error={fieldErr["general.org_name"]}
                onChange={(e) => setDraft({ ...draft, general: { ...draft.general, org_name: e.target.value } })}
              />
              <TextArea
                label="Report footer / disclaimer"
                value={draft.general.report_footer}
                maxLength={2000}
                onChange={(e) => setDraft({ ...draft, general: { ...draft.general, report_footer: e.target.value } })}
              />
              <TextField
                label="Auto-confirm threshold (AI confidence 0.50–1.00)"
                type="number"
                min={0.5}
                max={1}
                step={0.01}
                value={draft.general.auto_confirm_threshold}
                error={fieldErr["general.auto_confirm_threshold"]}
                hint="Fields at or above this confidence that pass format checks are confirmed automatically."
                onChange={(e) => setDraft({ ...draft, general: { ...draft.general, auto_confirm_threshold: Number(e.target.value) } })}
              />
            </div>
          )}
          {tab === "ai" && (
            <div className="flex flex-col gap-4">
              <h2 className="cs-h2">AI & OCR</h2>
              <p className="m-0" style={{ fontSize: 14, color: "#55584E" }}>
                Providers are tried in this order. Keys live only in the server environment and are never shown here.
              </p>
              <table className="cs-table">
                <thead>
                  <tr>
                    <th>Order</th>
                    <th>Provider</th>
                    <th>Model</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {s?.providers.map((p) => (
                    <tr key={p.name}>
                      <td>{p.position}</td>
                      <td>
                        <strong>{p.name}</strong>
                      </td>
                      <td>
                        <span className="cs-cell-label">Model</span>
                        {p.model ?? "—"}
                      </td>
                      <td>
                        <Chip tone={p.configured ? "ok" : "neu"}>{p.configured ? "Configured" : "No key"}</Chip>
                      </td>
                    </tr>
                  ))}
                  <tr>
                    <td>{(s?.providers.length ?? 0) + 1}</td>
                    <td>
                      <strong>OCR fallback (PaddleOCR)</strong>
                    </td>
                    <td>—</td>
                    <td>
                      <Chip tone={s?.ocr_available ? "ok" : "neu"}>{s?.ocr_available ? "Available" : "Not installed / disabled"}</Chip>
                    </td>
                  </tr>
                </tbody>
              </table>
              <label className="flex items-center gap-2.5" style={{ fontSize: 14 }}>
                <input
                  type="checkbox"
                  className="accent-[#3E5228]"
                  checked={draft.ai.ocr_fallback_enabled}
                  onChange={(e) => setDraft({ ...draft, ai: { ...draft.ai, ocr_fallback_enabled: e.target.checked } })}
                />
                Use the OCR fallback when every AI provider fails (only works where OCR is installed)
              </label>
              <label className="flex items-center gap-2.5" style={{ fontSize: 14 }}>
                <input
                  type="checkbox"
                  className="accent-[#3E5228]"
                  checked={draft.ai.web_research_enabled}
                  onChange={(e) => setDraft({ ...draft, ai: { ...draft.ai, web_research_enabled: e.target.checked } })}
                />
                Allow inspectors to switch on internet research in Ask AI (off by default for each question)
              </label>
            </div>
          )}
          {tab === "limits" && (
            <div className="flex flex-col gap-4 max-w-[640px]">
              <h2 className="cs-h2">Limits & Usage</h2>
              <TextField
                label="AI requests per user per day"
                type="number"
                min={1}
                max={10000}
                value={draft.limits.ai_daily_limit_per_user}
                error={fieldErr["limits.ai_daily_limit_per_user"]}
                hint="Keeps usage inside free API tiers. Paid usage is never enabled automatically."
                onChange={(e) => setDraft({ ...draft, limits: { ...draft.limits, ai_daily_limit_per_user: Number(e.target.value) } })}
              />
              <TextField
                label="Keep unfinished-inspection photos for (days)"
                type="number"
                min={1}
                max={90}
                value={draft.limits.photo_retention_days}
                error={fieldErr["limits.photo_retention_days"]}
                hint="Originals are deleted when the report is generated, or after this many days if the inspection is abandoned."
                onChange={(e) => setDraft({ ...draft, limits: { ...draft.limits, photo_retention_days: Number(e.target.value) } })}
              />
              <p className="m-0" style={{ fontSize: 14 }}>
                AI requests today across all users: <strong>{s?.usage_today ?? 0}</strong>
              </p>
            </div>
          )}
          {tab !== "images" && (
            <div className="flex flex-wrap items-center justify-between gap-3 mt-6 pt-4 border-t border-line cs-bar">
              <span style={{ fontSize: 12.5, color: "#686B60" }}>
                Changes here are written to the audit log.
                {s?.updated_at ? ` Last saved ${fmtDate(s.updated_at, true)} by ${s.updated_by_name ?? "—"}.` : ""}
              </span>
              <div className="flex gap-2.5 cs-acts">
                <Button variant="secondary" disabled={!dirty} onClick={() => setDraft(s)}>
                  Cancel
                </Button>
                <Button icon="check" disabled={!dirty} working={busy === "save"} onClick={() => void save()}>
                  Save settings
                </Button>
              </div>
            </div>
          )}
          {tab === "images" && (
            <p className="mb-0 mt-4" style={{ fontSize: 12.5, color: "#686B60" }}>
              Image changes apply immediately and are written to the audit log.
            </p>
          )}
        </Panel>
      )}
    </>
  );
}
