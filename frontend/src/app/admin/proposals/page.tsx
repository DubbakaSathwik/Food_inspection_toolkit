"use client";

import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icon";
import { fromRecord, type RefForm, ReferenceFormFields, toPayload } from "@/components/reference-form";
import { PageHeader } from "@/components/shell";
import {
  Button,
  CATEGORY_LABELS,
  Chip,
  Empty,
  ErrorBox,
  fmtDate,
  LoadingBlock,
  Metric,
  Notice,
  Panel,
  SearchBox,
  SelectField,
  TextArea,
} from "@/components/ui";
import { ApiError, api, apiBlob, errorMessage, type Page, type Proposal } from "@/lib/api";

export default function AdminProposals() {
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const [data, setData] = useState<Page<Proposal> | null>(null);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [sel, setSel] = useState<Proposal | null>(null);
  const [form, setForm] = useState<RefForm | null>(null);
  const [editRef, setEditRef] = useState(false);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [fieldErr, setFieldErr] = useState<Record<string, string>>({});
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(() => {
    api<Page<Proposal>>("/api/v1/admin/proposals", { query: { status, page_size: 100 } })
      .then(setData)
      .catch((e) => setErr(errorMessage(e)));
    Promise.all(
      ["pending", "info_requested", "approved", "rejected"].map((s) =>
        api<Page<Proposal>>("/api/v1/admin/proposals", { query: { status: s, page_size: 1 } }).then((p) => [s, p.total] as const),
      ),
    )
      .then((r) => setCounts(Object.fromEntries(r)))
      .catch(() => undefined);
  }, [status]);
  useEffect(load, [load]);
  useEffect(() => {
    const open = new URLSearchParams(window.location.search).get("open");
    if (open)
      api<Proposal>(`/api/v1/admin/proposals/${open}`)
        .then(select)
        .catch(() => undefined);
  }, []);

  function select(p: Proposal) {
    const prod = p.product as Record<string, string>;
    setSel(p);
    setNote("");
    setEditRef(false);
    setFieldErr({});
    setForm(
      fromRecord({
        ...prod,
        gtin: prod.gtin ?? "",
        manufacturer: { name: prod.manufacturer_name, facility_address: prod.manufacturer_address },
        licence: { number: prod.fssai_licence, status: "active" },
      }),
    );
  }
  async function decide(outcome: string) {
    if (!sel || !form) return;
    setBusy(outcome);
    setErr(null);
    setFieldErr({});
    try {
      const body: Record<string, unknown> = { outcome, note };
      if (outcome === "approved" && editRef) body.reference = { ...toPayload(form), source: "proposal" };
      const u = await api<Proposal>(`/api/v1/admin/proposals/${sel.id}/decision`, { method: "POST", body });
      setSel(u);
      setNotice(
        outcome === "approved"
          ? `Approved — demo reference record ${u.reference_id} created.`
          : `Proposal ${u.id} marked ${outcome.replace("_", " ")}.`,
      );
      load();
    } catch (e) {
      if (e instanceof ApiError && e.fields)
        setFieldErr(Object.fromEntries(Object.entries(e.fields).map(([k, v]) => [k.replace(/^reference\./, ""), v])));
      setErr(errorMessage(e));
    } finally {
      setBusy(null);
    }
  }
  async function openPdf() {
    if (!sel) return;
    try {
      window.open(URL.createObjectURL(await apiBlob(`/api/v1/admin/proposals/${sel.id}/report.pdf`)), "_blank", "noopener");
    } catch (e) {
      setErr(errorMessage(e));
    }
  }

  const items = (data?.items ?? []).filter((p) => {
    if (!q) return true;
    const prod = p.product as Record<string, string>;
    return [prod.product_name, prod.brand, p.owner_name, p.id].join(" ").toLowerCase().includes(q.toLowerCase());
  });
  const prod = (sel?.product ?? {}) as Record<string, string>;
  const decided = sel && ["approved", "rejected"].includes(sel.status);
  return (
    <>
      <PageHeader title="Product Proposals" subtitle="Products submitted by inspectors for the reference database." />
      <Notice>
        Approving a proposal creates a demonstration reference record. It does not certify the product or verify its licence with any
        authority.
      </Notice>
      {notice && (
        <Notice tone="ok" icon="check">
          {notice}
        </Notice>
      )}
      {err && <ErrorBox error={err} />}
      <div className="grid gap-4 cs-grid" style={{ gridTemplateColumns: "repeat(4, minmax(0, 1fr))" }}>
        <Metric icon="clock" value={counts.pending ?? "—"} labelText="Pending" highlight />
        <Metric icon="info" value={counts.info_requested ?? "—"} labelText="Information requested" />
        <Metric icon="check" value={counts.approved ?? "—"} labelText="Approved" />
        <Metric icon="x" value={counts.rejected ?? "—"} labelText="Rejected" />
      </div>
      <Panel>
        <div className="flex flex-wrap items-end gap-3 mb-4">
          <div className="flex-[1_1_260px] max-w-[360px]">
            <SearchBox value={q} onChange={setQ} placeholder="Product, brand or inspector" />
          </div>
          <SelectField label="Status" value={status} onChange={(e) => setStatus(e.target.value)} className="w-[180px]">
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="info_requested">Info requested</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </SelectField>
        </div>
        {!data ? (
          <LoadingBlock />
        ) : items.length === 0 ? (
          <Empty icon="proposal" title="No proposals" />
        ) : (
          <table className="cs-table">
            <thead>
              <tr>
                <th>Product Name</th>
                <th>Brand</th>
                <th>Submitted By</th>
                <th>Submission Date</th>
                <th>Status</th>
                <th>Review Action</th>
              </tr>
            </thead>
            <tbody>
              {items.map((p) => {
                const pr = p.product as Record<string, string>;
                return (
                  <tr key={p.id} style={sel?.id === p.id ? { background: "#EEF2E1" } : undefined}>
                    <td>
                      <strong>{pr.product_name}</strong>
                      <div style={{ fontSize: 12, color: "#686B60" }}>{p.id}</div>
                    </td>
                    <td>
                      <span className="cs-cell-label">Brand</span>
                      {pr.brand}
                    </td>
                    <td>
                      <span className="cs-cell-label">Submitted by</span>
                      {p.owner_name}
                    </td>
                    <td>
                      <span className="cs-cell-label">Date</span>
                      {fmtDate(p.created_at)}
                    </td>
                    <td>
                      <Chip status={p.status} />
                    </td>
                    <td>
                      <button
                        type="button"
                        className="inline-flex items-center gap-1 font-semibold bg-transparent border-0 cursor-pointer whitespace-nowrap"
                        style={{ color: "#56703A", fontSize: 14 }}
                        onClick={() => {
                          select(p);
                          setTimeout(() => document.getElementById("review")?.scrollIntoView({ behavior: "smooth" }), 50);
                        }}
                      >
                        {sel?.id === p.id ? "Reviewing" : "Review"}
                        <Icon name="chev" size={15} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Panel>
      {sel && form && (
        <Panel id="review">
          <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
            <div>
              <h2 className="cs-h2">Reviewing: {prod.product_name}</h2>
              <p className="m-0 mt-1" style={{ fontSize: 13.5, color: "#55584E" }}>
                Submitted by {sel.owner_name} · {fmtDate(sel.created_at)} · inspection {sel.inspection_id} · <Chip status={sel.status} />
              </p>
            </div>
            <Button variant="secondary" icon="doc" disabled={!sel.has_report} onClick={() => void openPdf()}>
              Open inspection PDF
            </Button>
          </div>
          <div className="grid grid-cols-2 gap-6 max-[960px]:grid-cols-1">
            <div>
              <h3 style={{ fontSize: 15, margin: "0 0 10px" }}>Submitted details</h3>
              <dl className="grid grid-cols-2 gap-x-5 gap-y-3 m-0" style={{ fontSize: 14 }}>
                {[
                  ["Product name", prod.product_name],
                  ["Brand", prod.brand],
                  ["Category", CATEGORY_LABELS[prod.category]],
                  ["Variant", prod.variant],
                  ["Manufacturer", prod.manufacturer_name],
                  ["Licence number", prod.fssai_licence],
                  ["Address", prod.manufacturer_address],
                  ["Net quantity", prod.net_quantity],
                  ["Barcode / GTIN", prod.gtin],
                ].map(([k, v]) => (
                  <div key={k} className="min-w-0">
                    <dt className="cs-label">{k}</dt>
                    <dd className="m-0 font-bold" style={{ overflowWrap: "anywhere" }}>
                      {v || "—"}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
            <div className="flex flex-col gap-3">
              <h3 style={{ fontSize: 15, margin: 0 }}>Evidence</h3>
              <p className="m-0" style={{ fontSize: 13.5, color: "#55584E" }}>
                {sel.photo_count} photograph{sel.photo_count === 1 ? " is" : "s are"} embedded in the inspection PDF (originals are not kept
                separately).
              </p>
              <div className="rounded-[10px] p-3" style={{ background: "#FBF3E6", fontSize: 13.5 }}>
                <strong>Inspector remarks:</strong> {sel.remarks || "—"}
              </div>
              {(sel.messages as { from: string; by: string; text: string; at: string }[]).map((m, i) => (
                <div
                  key={i}
                  className="rounded-[10px] p-3"
                  style={{ background: m.from === "admin" ? "#E2E8EE" : "#FBF8F0", fontSize: 13.5 }}
                >
                  <strong>{m.from === "admin" ? `${m.by} asked` : `${m.by} replied`}</strong> · {fmtDate(m.at, true)}
                  <div>{m.text}</div>
                </div>
              ))}
            </div>
          </div>
          {!decided ? (
            <div className="mt-6 pt-5 border-t border-line flex flex-col gap-4">
              <label className="flex items-center gap-2" style={{ fontSize: 14 }}>
                <input type="checkbox" checked={editRef} onChange={(e) => setEditRef(e.target.checked)} className="accent-[#3E5228]" />
                Correct the details before approving (corrections are recorded in the audit log)
              </label>
              {editRef && <ReferenceFormFields value={form} onChange={setForm} errors={fieldErr} />}
              <TextArea
                label="Note to the inspector (required to reject or request information)"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                maxLength={8000}
              />
              <div className="flex flex-wrap gap-2.5 cs-acts">
                <Button icon="check" working={busy === "approved"} onClick={() => void decide("approved")}>
                  Approve
                </Button>
                <Button
                  variant="secondary"
                  icon="info"
                  working={busy === "info_requested"}
                  disabled={!note.trim()}
                  onClick={() => void decide("info_requested")}
                >
                  Request information
                </Button>
                <Button
                  variant="danger"
                  icon="x"
                  working={busy === "rejected"}
                  disabled={!note.trim()}
                  onClick={() => void decide("rejected")}
                >
                  Reject
                </Button>
                <Button variant="secondary" working={busy === "pending"} onClick={() => void decide("pending")}>
                  Keep pending
                </Button>
              </div>
            </div>
          ) : (
            <div className="mt-6 pt-5 border-t border-line" style={{ fontSize: 14 }}>
              Decision: <Chip status={sel.status} />{" "}
              {sel.reference_id && (
                <>
                  {" "}
                  · demo reference record <a href={`/admin/reference/${sel.reference_id}`}>{sel.reference_id}</a>
                </>
              )}
            </div>
          )}
        </Panel>
      )}
    </>
  );
}
