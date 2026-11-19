"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { Icon } from "@/components/icon";
import { emptyRef, fromRecord, type RefForm, ReferenceFormFields, toPayload, useRefSubmit } from "@/components/reference-form";
import { PageHeader } from "@/components/shell";
import {
  Button,
  CATEGORY_LABELS,
  Chip,
  Empty,
  ErrorBox,
  fmtDate,
  IconButton,
  LoadingBlock,
  Modal,
  Notice,
  Panel,
  SearchBox,
  SelectField,
} from "@/components/ui";
import { api, errorMessage, type Page, type Reference, type S } from "@/lib/api";

type Mode = null | "menu" | "manual" | "ai" | "import";

export default function ReferenceDatabase() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("active");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<Reference> | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>(null);
  const [form, setForm] = useState<RefForm>(emptyRef());
  const [archiveTarget, setArchiveTarget] = useState<Reference | null>(null);
  const sub = useRefSubmit();

  const load = useCallback(() => {
    api<Page<Reference>>("/api/v1/admin/reference", { query: { q, category, status, page, page_size: 20 } })
      .then(setData)
      .catch((e) => setErr(errorMessage(e)));
  }, [q, category, status, page]);
  useEffect(() => {
    const t = window.setTimeout(load, 250);
    return () => window.clearTimeout(t);
  }, [load]);

  async function create(source: "manual" | "ai_assisted") {
    const r = await sub.run(() => api<Reference>("/api/v1/admin/reference", { method: "POST", body: { ...toPayload(form), source } }));
    if (r) router.push(`/admin/reference/${r.id}`);
  }
  async function archive(r: Reference) {
    try {
      await api(`/api/v1/admin/reference/${r.id}/${r.status === "archived" ? "restore" : "archive"}`, { method: "POST" });
      setArchiveTarget(null);
      load();
    } catch (e) {
      setErr(errorMessage(e));
    }
  }
  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <>
      <PageHeader
        title="Reference Database"
        subtitle="Demonstration product, manufacturer, licence and packaging records used for matching."
      />
      <Notice>All records here are fictional demonstration data. Approving or adding a record does not make it officially verified.</Notice>
      {err && <ErrorBox error={err} onRetry={load} />}
      <Panel>
        <div className="flex flex-wrap items-end gap-3 mb-4">
          <div className="flex-[2_1_240px] min-w-0">
            <SearchBox
              value={q}
              onChange={(v) => {
                setQ(v);
                setPage(1);
              }}
              placeholder="Product, brand, manufacturer or licence"
            />
          </div>
          <SelectField
            label="Category"
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              setPage(1);
            }}
            className="flex-[1_1_180px]"
          >
            <option value="">All categories</option>
            {Object.entries(CATEGORY_LABELS)
              .filter(([k]) => k !== "all")
              .map(([k, l]) => (
                <option key={k} value={k}>
                  {l}
                </option>
              ))}
          </SelectField>
          <SelectField
            label="Status"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
            className="flex-[0_1_130px]"
          >
            <option value="active">Active</option>
            <option value="archived">Archived</option>
            <option value="all">All</option>
          </SelectField>
          <div className="ml-auto max-[760px]:w-full">
            <Button
              iconRight="plus"
              className="max-[760px]:w-full"
              onClick={() => {
                setForm(emptyRef());
                setMode("menu");
              }}
            >
              Add Product
            </Button>
          </div>
        </div>
        {!data ? (
          <LoadingBlock rows={6} />
        ) : data.items.length === 0 ? (
          <Empty icon="box" title="No records match">
            Change the filters or add a product.
          </Empty>
        ) : (
          <table className="cs-table">
            <thead>
              <tr>
                <th>Product Name</th>
                <th>Brand</th>
                <th>Category</th>
                <th>Manufacturer</th>
                <th>Last Updated</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((r) => (
                <tr key={r.id}>
                  <td>
                    <strong>{r.product_name}</strong>
                    <div style={{ fontSize: 12, color: "#686B60" }}>
                      {r.id}
                      {r.net_quantity ? ` · ${r.net_quantity}` : ""}
                    </div>
                  </td>
                  <td>
                    <span className="cs-cell-label">Brand</span>
                    {r.brand}
                  </td>
                  <td>
                    <span className="cs-cell-label">Category</span>
                    {CATEGORY_LABELS[r.category]}
                  </td>
                  <td>
                    <span className="cs-cell-label">Manufacturer</span>
                    {r.manufacturer.name || "—"}
                  </td>
                  <td>
                    <span className="cs-cell-label">Last updated</span>
                    {fmtDate(r.updated_at)}
                  </td>
                  <td>
                    <Chip status={r.status} />
                  </td>
                  <td>
                    <div className="flex gap-2">
                      <Link href={`/admin/reference/${r.id}`} className="cs-ib" aria-label={`View ${r.product_name}`} title="View">
                        <Icon name="eye" size={17} />
                      </Link>
                      <Link href={`/admin/reference/${r.id}?edit=1`} className="cs-ib" aria-label={`Edit ${r.product_name}`} title="Edit">
                        <Icon name="edit" size={17} />
                      </Link>
                      <IconButton
                        icon={r.status === "archived" ? "refresh" : "trash"}
                        label={r.status === "archived" ? `Restore ${r.product_name}` : `Archive ${r.product_name}`}
                        onClick={() => setArchiveTarget(r)}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div className="flex flex-wrap items-center justify-between gap-3 mt-4">
          <span style={{ fontSize: 13, color: "#55584E" }}>
            {data
              ? `Showing ${data.items.length ? (page - 1) * data.page_size + 1 : 0}–${(page - 1) * data.page_size + data.items.length} of ${data.total} records`
              : ""}
          </span>
          <div className="flex gap-2">
            <Button small variant="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>
              Previous
            </Button>
            <Button small variant="secondary" disabled={page >= pages} onClick={() => setPage(page + 1)}>
              Next
            </Button>
          </div>
        </div>
      </Panel>

      <Modal open={mode === "menu"} title="Add Product" onClose={() => setMode(null)}>
        <div className="flex flex-col gap-2.5">
          {(
            [
              ["manual", "edit", "Manual entry", "Type the product, manufacturer and demo licence details."],
              ["ai", "sparkle", "AI-assisted entry", "Upload pack photographs; the AI drafts the record for you to review."],
              ["import", "sheet", "Excel / CSV import", "Upload many records at once with a validation preview."],
            ] as const
          ).map(([m, i, t, d]) => (
            <button
              key={m}
              type="button"
              className="cs-card flex gap-3 rounded-[10px] border border-line p-4 text-left bg-white cursor-pointer"
              onClick={() => setMode(m)}
            >
              <span
                className="grid place-items-center rounded-[8px] shrink-0"
                style={{ width: 36, height: 36, background: "#EEF2E1", color: "#56703A" }}
              >
                <Icon name={i} />
              </span>
              <span>
                <strong className="block">{t}</strong>
                <span style={{ fontSize: 13.5, color: "#55584E" }}>{d}</span>
              </span>
            </button>
          ))}
        </div>
      </Modal>
      <Modal
        open={mode === "manual"}
        title="Add product — manual entry"
        onClose={() => setMode(null)}
        wide
        footer={
          <>
            <Button variant="secondary" onClick={() => setMode(null)}>
              Cancel
            </Button>
            <Button working={sub.busy} onClick={() => void create("manual")}>
              Save record
            </Button>
          </>
        }
      >
        {sub.err && (
          <div className="mb-3">
            <ErrorBox error={sub.err} />
          </div>
        )}
        <ReferenceFormFields value={form} onChange={setForm} errors={sub.errors} />
      </Modal>
      <AiEntry
        open={mode === "ai"}
        onClose={() => setMode(null)}
        onDraft={(f) => {
          setForm(f);
          setMode("manual");
        }}
      />
      <ImportDialog
        open={mode === "import"}
        onClose={() => setMode(null)}
        onDone={() => {
          setMode(null);
          load();
        }}
      />
      <Modal
        open={!!archiveTarget}
        title={archiveTarget?.status === "archived" ? "Restore record?" : "Archive record?"}
        onClose={() => setArchiveTarget(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setArchiveTarget(null)}>
              Cancel
            </Button>
            <Button
              variant={archiveTarget?.status === "archived" ? "primary" : "danger"}
              onClick={() => archiveTarget && void archive(archiveTarget)}
            >
              {archiveTarget?.status === "archived" ? "Restore" : "Archive"}
            </Button>
          </>
        }
      >
        <p className="m-0" style={{ fontSize: 14.5 }}>
          {archiveTarget?.status === "archived"
            ? "The record will be used for matching again."
            : "Archived records are not used for matching. You can restore them later. Only a Super Admin can delete permanently."}{" "}
          <strong>
            {archiveTarget?.brand} {archiveTarget?.product_name}
          </strong>
        </p>
      </Modal>
    </>
  );
}

function AiEntry({ open, onClose, onDraft }: { open: boolean; onClose: () => void; onDraft: (f: RefForm) => void }) {
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  async function run() {
    setBusy(true);
    setErr(null);
    try {
      const fd = new FormData();
      files.forEach((f) => fd.append("files", f));
      const r = await api<S["AiDraftOut"]>("/api/v1/admin/reference/ai-extract", { method: "POST", form: fd });
      onDraft(fromRecord(r.draft));
      setFiles([]);
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      open={open}
      title="AI-assisted entry"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button icon="sparkle" working={busy} disabled={!files.length} onClick={() => void run()}>
            Draft record
          </Button>
        </>
      }
    >
      <p className="mt-0" style={{ fontSize: 14, color: "#55584E" }}>
        Upload 1–5 pack photographs. Nothing is saved until you review the draft and press Save.
      </p>
      {err && (
        <div className="mb-3">
          <ErrorBox error={err} />
        </div>
      )}
      <input
        ref={input}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        hidden
        onChange={(e) => setFiles(Array.from(e.target.files ?? []).slice(0, 5))}
      />
      <Button variant="secondary" icon="upload" onClick={() => input.current?.click()}>
        Choose photographs
      </Button>
      <ul className="mb-0" style={{ fontSize: 13.5 }}>
        {files.map((f) => (
          <li key={f.name}>{f.name}</li>
        ))}
      </ul>
    </Modal>
  );
}

type Preview = S["ImportPreviewOut"];
function ImportDialog({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: () => void }) {
  const [preview, setPreview] = useState<Preview | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [result, setResult] = useState<number | null>(null);
  const input = useRef<HTMLInputElement>(null);
  async function upload(f: File) {
    setBusy(true);
    setErr(null);
    setPreview(null);
    setResult(null);
    try {
      const fd = new FormData();
      fd.append("file", f);
      setPreview(await api<Preview>("/api/v1/admin/reference/import/preview", { method: "POST", form: fd }));
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  async function commit() {
    if (!preview) return;
    setBusy(true);
    setErr(null);
    try {
      const rows = preview.rows.filter((r) => !Object.keys(r.errors).length).map((r) => r.data);
      const r = await api<{ created: number }>("/api/v1/admin/reference/import/commit", { method: "POST", body: { rows } });
      setResult(r.created);
      setPreview(null);
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      open={open}
      title="Excel / CSV import"
      onClose={result !== null ? onDone : onClose}
      wide
      footer={
        <>
          <Button variant="secondary" onClick={result !== null ? onDone : onClose}>
            {result !== null ? "Done" : "Cancel"}
          </Button>
          {preview && (
            <Button working={busy} disabled={!preview.valid} onClick={() => void commit()}>
              Import {preview.valid} valid row{preview.valid === 1 ? "" : "s"}
            </Button>
          )}
        </>
      }
    >
      <p className="mt-0" style={{ fontSize: 13.5, color: "#55584E" }}>
        Required columns: <code>product_name, brand, category</code>. Optional: net_quantity, package_sizes (separated by ;), gtin,
        manufacturer_name, registered_address, facility_address, state, district, contact, licence_number, licence_valid_from,
        licence_valid_until, licence_status, fbo_category, notes.
      </p>
      {err && (
        <div className="mb-3">
          <ErrorBox error={err} />
        </div>
      )}
      {result !== null && (
        <Notice tone="ok" icon="check">
          Imported {result} record{result === 1 ? "" : "s"}.
        </Notice>
      )}
      <input
        ref={input}
        type="file"
        accept=".csv,.xlsx"
        hidden
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void upload(f);
          e.target.value = "";
        }}
      />
      <Button variant="secondary" icon="upload" working={busy && !preview} onClick={() => input.current?.click()}>
        Choose .csv or .xlsx file
      </Button>
      {preview && (
        <div className="mt-4">
          <p style={{ fontSize: 13.5 }}>
            <strong>{preview.valid}</strong> valid · <strong style={{ color: "#86301E" }}>{preview.invalid}</strong> with errors (skipped)
          </p>
          <div className="max-h-[320px] overflow-y-auto">
            <table className="cs-table">
              <thead>
                <tr>
                  <th>Row</th>
                  <th>Product</th>
                  <th>Brand</th>
                  <th>Result</th>
                </tr>
              </thead>
              <tbody>
                {preview.rows.map((r) => {
                  const d = (r.data ?? {}) as Record<string, string>;
                  const errs = Object.entries(r.errors);
                  return (
                    <tr key={r.row}>
                      <td>{r.row}</td>
                      <td>{d.product_name || "—"}</td>
                      <td>{d.brand || "—"}</td>
                      <td>
                        {errs.length ? (
                          <span style={{ color: "#86301E", fontSize: 13 }}>{errs.map(([k, v]) => `${k}: ${v}`).join("; ")}</span>
                        ) : (
                          <Chip status="pass">Valid</Chip>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </Modal>
  );
}
