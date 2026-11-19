"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { AuthImage } from "@/components/media";
import { fromRecord, type RefForm, ReferenceFormFields, toPayload, useRefSubmit } from "@/components/reference-form";
import { PageHeader } from "@/components/shell";
import {
  Backlink,
  Button,
  CATEGORY_LABELS,
  Chip,
  ErrorBox,
  fmtDate,
  IconButton,
  label,
  LoadingBlock,
  Modal,
  Notice,
  Panel,
  TextField,
} from "@/components/ui";
import { api, errorMessage, type Page, type Reference, type S } from "@/lib/api";
import { useAuth } from "@/lib/auth";

function Info({ rows }: { rows: [string, string | null | undefined][] }) {
  return (
    <dl className="grid grid-cols-2 gap-x-6 gap-y-3.5 m-0 max-[760px]:grid-cols-1" style={{ fontSize: 14 }}>
      {rows.map(([k, v]) => (
        <div key={k} className="min-w-0">
          <dt className="cs-label">{k}</dt>
          <dd className="m-0 font-bold" style={{ overflowWrap: "anywhere" }}>
            {v || "—"}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export default function ProductDetail() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { me } = useAuth();
  const [r, setR] = useState<Reference | null>(null);
  const [history, setHistory] = useState<S["AuditOut"][]>([]);
  const [editing, setEditing] = useState(false);
  const [vals, setVals] = useState<RefForm | null>(null);
  const [saved, setSaved] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<"archive" | "delete" | null>(null);
  const [versionOpen, setVersionOpen] = useState(false);
  const [vLabel, setVLabel] = useState("");
  const [uploadTo, setUploadTo] = useState<{ version: string; side: string } | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const sub = useRefSubmit();

  const load = useCallback(() => {
    api<Reference>(`/api/v1/admin/reference/${id}`)
      .then((x) => {
        setR(x);
        setVals(fromRecord(x));
        if (new URLSearchParams(window.location.search).get("edit") === "1") setEditing(true);
      })
      .catch((e) => setErr(errorMessage(e)));
    api<Page<S["AuditOut"]>>("/api/v1/admin/audit", { query: { q: id, page_size: 10 } })
      .then((p) => setHistory(p.items))
      .catch(() => undefined);
  }, [id]);
  useEffect(load, [load]);

  async function save() {
    if (!vals) return;
    const res = await sub.run(() => api<Reference>(`/api/v1/admin/reference/${id}`, { method: "PATCH", body: toPayload(vals) }));
    if (res) {
      setR(res);
      setVals(fromRecord(res));
      setEditing(false);
      setSaved(true);
      load();
    }
  }
  async function act(kind: "archive" | "delete") {
    try {
      if (kind === "delete") {
        await api(`/api/v1/admin/reference/${id}`, { method: "DELETE" });
        router.replace("/admin/reference");
        return;
      }
      setR(await api<Reference>(`/api/v1/admin/reference/${id}/${r?.status === "archived" ? "restore" : "archive"}`, { method: "POST" }));
      setConfirm(null);
      load();
    } catch (e) {
      setErr(errorMessage(e));
      setConfirm(null);
    }
  }
  async function addVersion() {
    const fd = new FormData();
    fd.append("label", vLabel.trim());
    try {
      setR(await api<Reference>(`/api/v1/admin/reference/${id}/versions`, { method: "POST", form: fd }));
      setVersionOpen(false);
      setVLabel("");
    } catch (e) {
      setErr(errorMessage(e));
    }
  }
  async function upload(f: File) {
    if (!uploadTo) return;
    const fd = new FormData();
    fd.append("file", f);
    fd.append("side", uploadTo.side);
    try {
      setR(await api<Reference>(`/api/v1/admin/reference/${id}/versions/${uploadTo.version}/images`, { method: "POST", form: fd }));
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setUploadTo(null);
    }
  }
  async function removeImage(fileId: string) {
    try {
      setR(await api<Reference>(`/api/v1/admin/reference/${id}/images/${fileId}`, { method: "DELETE" }));
    } catch (e) {
      setErr(errorMessage(e));
    }
  }

  if (!r || !vals)
    return (
      <>
        <PageHeader title="Reference record" back={<Backlink href="/admin/reference">Back to reference database</Backlink>} />
        {err ? (
          <ErrorBox error={err} />
        ) : (
          <Panel>
            <LoadingBlock rows={6} />
          </Panel>
        )}
      </>
    );
  const lic = r.licence as Record<string, string | null>;
  return (
    <>
      <PageHeader
        title={r.product_name}
        back={<Backlink href="/admin/reference">Back to reference database</Backlink>}
        subtitle={`${r.brand} · ${CATEGORY_LABELS[r.category]} · demonstration record · ${r.id}`}
        actions={<Chip status={r.status} />}
      />
      {err && <ErrorBox error={err} />}
      {saved && !editing && (
        <Notice tone="ok" icon="check">
          Changes saved and written to the audit log.
        </Notice>
      )}
      <div className="grid grid-cols-[minmax(0,1fr)_300px] gap-5 items-start max-[960px]:grid-cols-1">
        <div className="flex flex-col gap-5 min-w-0">
          {editing ? (
            <Panel title="Edit record">
              {sub.err && (
                <div className="mb-3">
                  <ErrorBox error={sub.err} />
                </div>
              )}
              <ReferenceFormFields value={vals} onChange={setVals} errors={sub.errors} />
              <div className="flex flex-wrap gap-2.5 mt-5 cs-acts">
                <Button working={sub.busy} onClick={() => void save()}>
                  Save changes
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => {
                    setEditing(false);
                    setVals(fromRecord(r));
                  }}
                >
                  Cancel
                </Button>
              </div>
            </Panel>
          ) : (
            <>
              <Panel title="Product identity">
                <Info
                  rows={[
                    ["Product name", r.product_name],
                    ["Brand", r.brand],
                    ["Category", CATEGORY_LABELS[r.category]],
                    ["Variant", r.variant],
                    ["Net quantity", r.net_quantity],
                    ["Package sizes", r.package_sizes.join("; ")],
                    ["Barcode / GTIN", r.gtin],
                    ["Source", label(r.source)],
                  ]}
                />
              </Panel>
              <Panel title="Manufacturer">
                <Info
                  rows={[
                    ["Company name", r.manufacturer.name],
                    ["Registered address", r.manufacturer.registered_address],
                    ["Manufacturing facility", r.manufacturer.facility_address],
                    ["State / district", [r.manufacturer.state, r.manufacturer.district].filter(Boolean).join(" / ")],
                    ["Contact", r.manufacturer.contact],
                  ]}
                />
              </Panel>
              <Panel title="Demonstration licence record">
                <Info
                  rows={[
                    ["Licence number", lic.number],
                    ["Licence status", `${label(lic.status)} (demo)`],
                    ["Valid from", lic.valid_from ? fmtDate(lic.valid_from) : null],
                    ["Valid until", lic.valid_until ? fmtDate(lic.valid_until) : null],
                    ["Food business category", lic.fbo_category],
                  ]}
                />
              </Panel>
            </>
          )}
          <Panel
            title="Reference packaging images"
            action={
              <Button small variant="secondary" icon="plus" onClick={() => setVersionOpen(true)}>
                Add version
              </Button>
            }
          >
            <p className="mt-0" style={{ fontSize: 13.5, color: "#55584E" }}>
              Used for packaging comparison. Keep known packaging versions so genuine redesigns are not reported as differences. The newest
              version with photos is compared.
            </p>
            {r.packaging_versions.length === 0 && <Notice>No packaging versions yet. Add a version, then upload its photographs.</Notice>}
            <div className="flex flex-col gap-4">
              {r.packaging_versions.map((v) => (
                <div key={v.id} className="rounded-[10px] border border-line p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                    <strong>
                      Version {v.label} <span style={{ fontSize: 12, fontWeight: 500, color: "#686B60" }}>· {fmtDate(v.created_at)}</span>
                    </strong>
                    <div className="flex gap-2 items-center">
                      <label className="sr-only" htmlFor={`side-${v.id}`}>
                        Side
                      </label>
                      <select
                        id={`side-${v.id}`}
                        className="cs-select"
                        style={{ width: "auto", minHeight: 36, padding: "4px 8px", fontSize: 13 }}
                        defaultValue="front"
                      >
                        <option value="front">Front</option>
                        <option value="back">Back</option>
                        <option value="side">Side</option>
                        <option value="closeup">Close-up</option>
                      </select>
                      <Button
                        small
                        variant="secondary"
                        icon="upload"
                        disabled={v.images.length >= 8}
                        onClick={(e) => {
                          const sel =
                            (e.currentTarget.parentElement?.querySelector("select") as HTMLSelectElement | null)?.value ?? "front";
                          setUploadTo({ version: v.id, side: sel });
                          fileInput.current?.click();
                        }}
                      >
                        Add image
                      </Button>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-3 cs-grid">
                    {v.images.map((im) => (
                      <figure key={im.file_id} className="m-0 relative">
                        <div className="overflow-hidden rounded-[8px]" style={{ height: 150, background: "#E8E5DA" }}>
                          <AuthImage path={`/api/v1/reference-images/${im.file_id}`} alt={`${im.side} · version ${v.label}`} />
                        </div>
                        <figcaption className="flex items-center justify-between mt-1" style={{ fontSize: 12.5 }}>
                          {label(im.side)} · version {v.label}
                          <IconButton icon="trash" label="Remove image" onClick={() => void removeImage(im.file_id)} />
                        </figcaption>
                      </figure>
                    ))}
                    {v.images.length === 0 && <span style={{ fontSize: 13, color: "#686B60" }}>No photographs in this version yet.</span>}
                  </div>
                </div>
              ))}
            </div>
            <input
              ref={fileInput}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              hidden
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void upload(f);
                e.target.value = "";
              }}
            />
          </Panel>
        </div>
        <div className="flex flex-col gap-5">
          <aside className="cs-panel flex flex-col gap-2.5" aria-label="Record actions">
            <h2 style={{ margin: "0 0 4px", fontSize: 16, fontWeight: 700 }}>Record actions</h2>
            {!editing && (
              <Button
                icon="edit"
                onClick={() => {
                  setEditing(true);
                  setSaved(false);
                }}
              >
                Edit record
              </Button>
            )}
            <Button variant="secondary" icon={r.status === "archived" ? "refresh" : "trash"} onClick={() => setConfirm("archive")}>
              {r.status === "archived" ? "Restore record" : "Archive record"}
            </Button>
            {me?.role === "super_admin" && (
              <Button variant="danger" icon="trash" onClick={() => setConfirm("delete")}>
                Delete permanently
              </Button>
            )}
          </aside>
          <aside className="cs-panel" aria-label="Record history">
            <h2 style={{ margin: "0 0 10px", fontSize: 16, fontWeight: 700 }}>Record history</h2>
            {history.length === 0 ? (
              <span style={{ fontSize: 13, color: "#686B60" }}>No changes recorded.</span>
            ) : (
              <ul className="list-none m-0 p-0 flex flex-col">
                {history.map((h) => (
                  <li key={h.id} className="flex gap-2.5 py-2.5 border-b border-line">
                    <span aria-hidden className="mt-1.5 shrink-0" style={{ width: 6, height: 6, borderRadius: 3, background: "#9CAB84" }} />
                    <span style={{ fontSize: 13 }}>
                      <strong className="block">{h.summary || h.action}</strong>
                      <span style={{ color: "#686B60" }}>
                        {h.actor_name} · {fmtDate(h.at, true)}
                      </span>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </aside>
        </div>
      </div>
      <Modal
        open={versionOpen}
        title="Add packaging version"
        onClose={() => setVersionOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setVersionOpen(false)}>
              Cancel
            </Button>
            <Button disabled={!vLabel.trim()} onClick={() => void addVersion()}>
              Add version
            </Button>
          </>
        }
      >
        <TextField label="Version label" value={vLabel} onChange={(e) => setVLabel(e.target.value)} placeholder="2026-A" maxLength={80} />
      </Modal>
      <Modal
        open={!!confirm}
        title={confirm === "delete" ? "Delete permanently?" : r.status === "archived" ? "Restore record?" : "Archive record?"}
        onClose={() => setConfirm(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirm(null)}>
              Cancel
            </Button>
            <Button variant={confirm === "delete" ? "danger" : "primary"} onClick={() => confirm && void act(confirm)}>
              Confirm
            </Button>
          </>
        }
      >
        <p className="m-0" style={{ fontSize: 14.5 }}>
          {confirm === "delete"
            ? "This removes the record and its packaging photographs. This cannot be undone."
            : r.status === "archived"
              ? "The record will be used for matching again."
              : "Archived records are not used for matching and can be restored later."}
        </p>
      </Modal>
    </>
  );
}
