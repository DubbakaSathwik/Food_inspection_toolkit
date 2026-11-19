"use client";

import { Fragment, useCallback, useEffect, useState } from "react";
import { Icon, type IconName } from "@/components/icon";
import { PageHeader } from "@/components/shell";
import {
  Button,
  ButtonLink,
  CATEGORY_LABELS,
  Chip,
  Empty,
  ErrorBox,
  fmtDate,
  LoadingBlock,
  Metric,
  Notice,
  Panel,
  TextArea,
} from "@/components/ui";
import { api, errorMessage, type Page, type Proposal } from "@/lib/api";

function latest(p: Proposal): string {
  const r = p.reviews.at(-1) as { note?: string; outcome?: string } | undefined;
  if (p.status === "pending") return p.messages.length ? "Your reply was sent — awaiting admin review" : "Awaiting admin review";
  return r?.note || (p.status === "approved" ? "Added to the demo reference database" : "—");
}

export default function InspectorProposals() {
  const [data, setData] = useState<Page<Proposal> | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const load = useCallback(() => {
    api<Page<Proposal>>("/api/v1/proposals", { query: { page_size: 100 } })
      .then(setData)
      .catch((e) => setErr(errorMessage(e)));
  }, []);
  useEffect(load, [load]);

  async function send(p: Proposal) {
    setBusy(true);
    try {
      const u = await api<Proposal>(`/api/v1/proposals/${p.id}/reply`, { method: "POST", body: { message: reply } });
      setData((d) => d && { ...d, items: d.items.map((x) => (x.id === u.id ? u : x)) });
      setReply("");
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  const items = data?.items ?? [];
  const n = (s: string) => items.filter((p) => p.status === s).length;
  const includes: [IconName, string][] = [
    ["file", "Product, brand and manufacturer details as extracted"],
    ["shield", "Licence information read from the pack"],
    ["doc", "The inspection PDF with the original photographs"],
    ["edit", "Your remarks for the administrator"],
  ];
  return (
    <>
      <PageHeader
        title="Product Proposals"
        subtitle="Products you submitted for the reference database."
        actions={
          <ButtonLink href="/inspector/history" iconRight="plus">
            New proposal
          </ButtonLink>
        }
      />
      <Notice>
        A proposal adds a product to the demonstration reference database once an administrator approves it. Approval is not official FSSAI
        certification. To submit one, open a completed inspection&apos;s report and choose &ldquo;Submit as proposal&rdquo;.
      </Notice>
      {err && <ErrorBox error={err} onRetry={load} />}
      <div className="grid gap-4 cs-grid" style={{ gridTemplateColumns: "repeat(4, minmax(0, 1fr))" }}>
        <Metric icon="proposal" value={data ? data.total : "—"} labelText="Total submitted" />
        <Metric icon="clock" value={data ? n("pending") : "—"} labelText="Pending" />
        <Metric icon="info" value={data ? n("info_requested") : "—"} labelText="Information requested" />
        <Metric icon="check" value={data ? n("approved") : "—"} labelText="Approved" />
      </div>
      <Panel title="Your proposals">
        {!data ? (
          <LoadingBlock />
        ) : items.length === 0 ? (
          <Empty icon="proposal" title="No proposals yet">
            Submit unknown products from a completed inspection report.
          </Empty>
        ) : (
          <table className="cs-table">
            <thead>
              <tr>
                <th>Product Name</th>
                <th>Brand</th>
                <th>Category</th>
                <th>Submitted</th>
                <th>Status</th>
                <th>Latest update</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {items.map((p) => {
                const prod = p.product as Record<string, string>;
                const isOpen = open === p.id;
                return (
                  <Fragment key={p.id}>
                    <tr>
                      <td>
                        <strong>{prod.product_name}</strong>
                        <div style={{ fontSize: 12, color: "#686B60" }}>{p.id}</div>
                      </td>
                      <td>
                        <span className="cs-cell-label">Brand</span>
                        {prod.brand}
                      </td>
                      <td>
                        <span className="cs-cell-label">Category</span>
                        {CATEGORY_LABELS[prod.category] ?? prod.category}
                      </td>
                      <td>
                        <span className="cs-cell-label">Submitted</span>
                        {fmtDate(p.created_at)}
                      </td>
                      <td>
                        <Chip status={p.status} />
                      </td>
                      <td>
                        <span className="cs-cell-label">Latest update</span>
                        <span style={{ fontSize: 13.5, color: "#55584E" }}>{latest(p)}</span>
                      </td>
                      <td>
                        <Button
                          small
                          variant="secondary"
                          aria-expanded={isOpen}
                          onClick={() => {
                            setOpen(isOpen ? null : p.id);
                            setReply("");
                          }}
                        >
                          {isOpen ? "Hide" : "View"}
                        </Button>
                      </td>
                    </tr>
                    {isOpen && (
                      <tr>
                        <td colSpan={7} style={{ background: "#FBF8F0" }}>
                          <div className="grid grid-cols-2 gap-4 max-[760px]:grid-cols-1 py-2" style={{ fontSize: 13.5 }}>
                            <div className="flex flex-col gap-1">
                              <strong>Submitted details</strong>
                              {[
                                ["Variant", prod.variant],
                                ["Net quantity", prod.net_quantity],
                                ["Manufacturer", prod.manufacturer_name],
                                ["Address", prod.manufacturer_address],
                                ["FSSAI licence", prod.fssai_licence],
                                ["Barcode / GTIN", prod.gtin],
                                ["Inspection", p.inspection_id],
                                ["Your remarks", p.remarks],
                              ].map(([k, v]) => (
                                <div key={k}>
                                  <span style={{ color: "#686B60" }}>{k}: </span>
                                  {v || "—"}
                                </div>
                              ))}
                            </div>
                            <div className="flex flex-col gap-2">
                              <strong>History</strong>
                              {[
                                ...p.reviews.map((r) => ({
                                  at: r.at as string,
                                  text: `${(r.outcome as string).replace("_", " ")} by ${r.by_name}${r.note ? `: ${r.note}` : ""}`,
                                })),
                                ...p.messages
                                  .filter((m) => m.from === "inspector")
                                  .map((m) => ({ at: m.at as string, text: `You replied: ${m.text}` })),
                              ]
                                .sort((a, b) => a.at.localeCompare(b.at))
                                .map((e, i) => (
                                  <div key={i} className="flex gap-2">
                                    <Icon name="clock" size={14} />
                                    <span>
                                      {fmtDate(e.at, true)} — {e.text}
                                    </span>
                                  </div>
                                ))}
                              {p.reviews.length === 0 && <span style={{ color: "#686B60" }}>No admin activity yet.</span>}
                              {p.status === "info_requested" && (
                                <div className="flex flex-col gap-2 mt-2">
                                  <TextArea
                                    label="Reply to the administrator"
                                    value={reply}
                                    onChange={(e) => setReply(e.target.value)}
                                    maxLength={8000}
                                  />
                                  <Button small working={busy} disabled={!reply.trim()} onClick={() => void send(p)}>
                                    Send reply
                                  </Button>
                                </div>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        )}
      </Panel>
      <Panel title="What a proposal includes">
        <div className="grid gap-3 cs-grid" style={{ gridTemplateColumns: "repeat(4, minmax(0, 1fr))" }}>
          {includes.map(([i, t]) => (
            <div
              key={t}
              className="flex gap-2.5 rounded-[10px] border border-line p-3.5"
              style={{ background: "#FBF8F0", fontSize: 13.5, lineHeight: 1.5 }}
            >
              <Icon name={i} size={16} />
              {t}
            </div>
          ))}
        </div>
      </Panel>
    </>
  );
}
