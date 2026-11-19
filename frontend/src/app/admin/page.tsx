"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icon";
import { PageHeader } from "@/components/shell";
import { CATEGORY_LABELS, Chip, Empty, ErrorBox, fmtDate, initials, LoadingBlock, Metric, Panel, TextLink } from "@/components/ui";
import { api, errorMessage, type S } from "@/lib/api";

type Dash = S["AdminDashboardOut"];

export default function AdminDashboard() {
  const [d, setD] = useState<Dash | null>(null);
  const [rules, setRules] = useState<S["RulesStatsOut"] | null>(null);
  const [cats, setCats] = useState<Record<string, number> | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const load = useCallback(() => {
    api<Dash>("/api/v1/admin/dashboard")
      .then((x) => {
        setD(x);
        setErr(null);
      })
      .catch((e) => setErr(errorMessage(e)));
    api<S["RulesStatsOut"]>("/api/v1/admin/rules/stats")
      .then(setRules)
      .catch(() => undefined);
    api<S["AnalyticsOut"]>("/api/v1/admin/analytics", { query: { range_days: 365 } })
      .then((a) => setCats(a.by_category))
      .catch(() => undefined);
  }, []);
  useEffect(load, [load]);
  const maxCat = Math.max(1, ...Object.values(cats ?? {}));

  return (
    <>
      <PageHeader title="Admin Dashboard" subtitle="Manage reference information and monitor inspection activity." />
      {err && <ErrorBox error={err} onRetry={load} />}
      <div className="grid gap-4 cs-grid" style={{ gridTemplateColumns: "repeat(4, minmax(0, 1fr))" }}>
        <Metric icon="box" value={d?.reference_products ?? "—"} labelText="Reference Products" highlight />
        <Metric icon="rules" value={rules?.active ?? "—"} labelText="Active Compliance Rules" />
        <Metric icon="proposal" value={d ? (d.proposals.pending ?? 0) : "—"} labelText="Pending Product Proposals" />
        <Metric icon="users" value={d?.inspectors ?? "—"} labelText="Registered Inspectors" />
      </div>
      <div className="grid grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)] gap-5 items-start max-[960px]:grid-cols-1">
        <Panel title="Product proposals awaiting review" action={<TextLink href="/admin/proposals">All proposals</TextLink>}>
          {!d ? (
            <LoadingBlock />
          ) : d.pending_proposals.length === 0 ? (
            <Empty icon="check" title="No proposals waiting" />
          ) : (
            <table className="cs-table">
              <thead>
                <tr>
                  <th>Product Name</th>
                  <th>Brand</th>
                  <th>Submitted By</th>
                  <th>Date</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {d.pending_proposals.map((p) => (
                  <tr key={String(p.id)}>
                    <td>
                      <strong>{String(p.product ?? "")}</strong>
                    </td>
                    <td>
                      <span className="cs-cell-label">Brand</span>
                      {String(p.brand ?? "")}
                    </td>
                    <td>
                      <span className="cs-cell-label">Submitted by</span>
                      {String(p.owner_name ?? "")}
                    </td>
                    <td>
                      <span className="cs-cell-label">Date</span>
                      {fmtDate(String(p.created_at))}
                    </td>
                    <td>
                      <Chip status={String(p.status)} />
                    </td>
                    <td>
                      <Link
                        href={`/admin/proposals?open=${p.id}`}
                        className="inline-flex items-center gap-1 no-underline font-semibold whitespace-nowrap"
                      >
                        Review
                        <Icon name="chev" size={15} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Panel>
        <Panel title="Accounts awaiting approval">
          {!d ? (
            <LoadingBlock rows={2} />
          ) : (
            <>
              <Chip tone="warn" dot={false}>
                {d.pending_approvals}
              </Chip>
              <p style={{ fontSize: 13.5, color: "#55584E" }}>
                New Google sign-ins cannot start inspections until an administrator activates the account.
              </p>
              <div className="flex flex-col gap-2.5">
                {d.pending_users.map((u) => (
                  <Link
                    key={String(u.uid)}
                    href={`/admin/users?status=pending`}
                    className="cs-card flex flex-col gap-2 rounded-[10px] border border-line p-3.5 no-underline"
                    style={{ background: "#FBF8F0", color: "#20231D" }}
                  >
                    <span className="flex items-center gap-2.5">
                      <span
                        className="grid place-items-center rounded-full shrink-0"
                        style={{ width: 32, height: 32, background: "#E3EACF", fontSize: 12, fontWeight: 700 }}
                      >
                        {initials(String(u.name))}
                      </span>
                      <span className="min-w-0">
                        <strong className="block" style={{ fontSize: 14 }}>
                          {String(u.name)}
                        </strong>
                        <span style={{ fontSize: 12.5, color: "#55584E", overflowWrap: "anywhere" }}>{String(u.email)}</span>
                      </span>
                    </span>
                    <span className="inline-flex items-center gap-1" style={{ fontSize: 13, fontWeight: 600, color: "#56703A" }}>
                      Review
                      <Icon name="chev" size={15} />
                    </span>
                  </Link>
                ))}
                {d.pending_users.length === 0 && <span style={{ fontSize: 13.5, color: "#686B60" }}>No accounts waiting.</span>}
              </div>
            </>
          )}
        </Panel>
      </div>
      <div className="grid grid-cols-2 gap-5 max-[960px]:grid-cols-1">
        <Panel title="Inspections by category" action={<TextLink href="/admin/analytics">Analytics</TextLink>}>
          {!cats ? (
            <LoadingBlock rows={4} />
          ) : (
            <div className="flex flex-col gap-3.5">
              {["staples", "snacks", "beverages", "dairy"].map((k, i) => (
                <div key={k}>
                  <div className="flex justify-between" style={{ fontSize: 13.5 }}>
                    <span>{CATEGORY_LABELS[k]}</span>
                    <strong>{cats[k] ?? 0}</strong>
                  </div>
                  <div className="h-2 rounded-full mt-1" style={{ background: "#EEF2E1" }}>
                    <div
                      className="h-2 rounded-full"
                      style={{ width: `${((cats[k] ?? 0) / maxCat) * 100}%`, background: ["#56703A", "#89986D", "#9CAB84", "#C5D89D"][i] }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </Panel>
        <Panel title="Recent admin activity" action={<TextLink href="/admin/audit">Audit logs</TextLink>}>
          {!d ? (
            <LoadingBlock rows={3} />
          ) : d.recent_activity.length === 0 ? (
            <Empty icon="logs" title="No admin activity yet" />
          ) : (
            <ul className="list-none m-0 p-0 flex flex-col">
              {d.recent_activity.slice(0, 6).map((a) => (
                <li key={String(a.id)} className="flex gap-3 py-3 border-b border-line">
                  <span aria-hidden className="mt-1.5 shrink-0" style={{ width: 7, height: 7, borderRadius: 4, background: "#9CAB84" }} />
                  <span>
                    <span style={{ fontSize: 14 }}>
                      <strong>{String(a.actor_name)}</strong> {String(a.summary || a.action)}
                    </span>
                    <span className="block" style={{ fontSize: 12.5, color: "#686B60" }}>
                      {fmtDate(String(a.at), true)}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </>
  );
}
