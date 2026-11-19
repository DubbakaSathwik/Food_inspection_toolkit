"use client";

import { useEffect, useState } from "react";
import { ColumnChart, HBarList, StackedShare } from "@/components/charts";
import { PageHeader } from "@/components/shell";
import { CATEGORY_LABELS, ErrorBox, LoadingBlock, Metric, Notice, Panel, SelectField } from "@/components/ui";
import { api, errorMessage, type S } from "@/lib/api";

type A = S["AnalyticsOut"];

function isoWeek(d: Date): string {
  const t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const day = t.getUTCDay() || 7;
  t.setUTCDate(t.getUTCDate() + 4 - day);
  const y = new Date(Date.UTC(t.getUTCFullYear(), 0, 1));
  return `W${Math.ceil(((t.getTime() - y.getTime()) / 86400000 + 1) / 7)}`;
}

export default function Analytics() {
  const [range, setRange] = useState(30);
  const [a, setA] = useState<A | null>(null);
  const [refs, setRefs] = useState<number | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    api<A>("/api/v1/admin/analytics", { query: { range_days: range } })
      .then(setA)
      .catch((e) => setErr(errorMessage(e)));
    api<{ active: number }>("/api/v1/admin/reference/stats")
      .then((s) => setRefs(s.active))
      .catch(() => undefined);
  }, [range]);

  const inRange = a?.inspections_by_day.reduce((s, d) => s + Number(d.count), 0) ?? 0;
  const weekly = (() => {
    if (!a) return [];
    const m = new Map<string, number>();
    const end = new Date();
    for (let i = Math.min(range, 84) - 1; i >= 0; i -= 7) m.set(isoWeek(new Date(end.getTime() - i * 86400000)), 0);
    for (const d of a.inspections_by_day) {
      const w = isoWeek(new Date(String(d.day)));
      if (m.has(w)) m.set(w, (m.get(w) ?? 0) + Number(d.count));
    }
    return [...m.entries()].map(([label, value]) => ({ label, value }));
  })();
  const st = a?.storage;
  const used = st ? st.storage_mb : 0;

  return (
    <>
      <PageHeader
        title="Analytics"
        subtitle="Platform activity across inspections, products, proposals and users."
        actions={
          <SelectField label="Period" value={String(range)} onChange={(e) => setRange(Number(e.target.value))} className="w-[170px]">
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
            <option value="365">Last 12 months</option>
          </SelectField>
        }
      />
      {err && <ErrorBox error={err} />}
      <div className="grid gap-4 cs-grid" style={{ gridTemplateColumns: "repeat(4, minmax(0, 1fr))" }}>
        <Metric icon="doc" value={a ? inRange : "—"} labelText={`Inspections (${range} days)`} />
        <Metric icon="users" value={a?.active.mau ?? "—"} labelText="Active users (30 days)" />
        <Metric icon="box" value={refs ?? "—"} labelText="Reference products" />
        <Metric icon="proposal" value={a ? Object.values(a.proposals).reduce((s, v) => s + v, 0) : "—"} labelText="Proposals submitted" />
      </div>
      {!a ? (
        <Panel>
          <LoadingBlock rows={6} />
        </Panel>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-5 max-[960px]:grid-cols-1">
            <Panel title="Inspections by category">
              <HBarList
                label="Inspections by category"
                rows={["staples", "snacks", "beverages", "dairy"].map((k) => ({ label: CATEGORY_LABELS[k], value: a.by_category[k] ?? 0 }))}
              />
            </Panel>
            <Panel title="Inspection classifications">
              <StackedShare
                parts={[
                  ["verified", "Verified"],
                  ["not_verified", "Not verified"],
                  ["suspicious", "Suspicious"],
                ].map(([k, l]) => ({ key: k, label: l, value: a.by_classification[k] ?? 0 }))}
              />
              <p className="mb-0" style={{ fontSize: 12.5, color: "#686B60" }}>
                Classification is recorded by the inspector, not assigned automatically by the system.
              </p>
            </Panel>
          </div>
          <Panel title="Inspections per week">
            <ColumnChart data={weekly} label="Inspections" />
          </Panel>
          <div className="grid grid-cols-2 gap-5 max-[960px]:grid-cols-1">
            <Panel title="Proposal status">
              <HBarList
                label="Proposal status"
                rows={[
                  ["approved", "Approved"],
                  ["pending", "Pending"],
                  ["info_requested", "Information requested"],
                  ["rejected", "Rejected"],
                ].map(([k, l]) => ({ label: l, value: a.proposals[k] ?? 0 }))}
              />
            </Panel>
            <Panel title="User activity">
              <HBarList
                label="User activity"
                rows={[
                  ["Daily active users", a.active.dau],
                  ["Weekly active users", a.active.wau],
                  ["Monthly active users", a.active.mau],
                  ["Registered inspectors", a.users.role_inspector ?? 0],
                ].map(([l, v]) => ({ label: String(l), value: Number(v) }))}
              />
            </Panel>
          </div>
          <div className="grid grid-cols-2 gap-5 max-[960px]:grid-cols-1">
            <Panel title="Frequently scanned products">
              {a.top_products.length === 0 ? (
                <p className="m-0" style={{ fontSize: 13.5, color: "#686B60" }}>
                  No inspections yet.
                </p>
              ) : (
                <table className="cs-table">
                  <thead>
                    <tr>
                      <th>Product</th>
                      <th>Brand</th>
                      <th>Inspections</th>
                    </tr>
                  </thead>
                  <tbody>
                    {a.top_products.map((p, i) => (
                      <tr key={i}>
                        <td>
                          <strong>{String(p.product)}</strong>
                        </td>
                        <td>
                          <span className="cs-cell-label">Brand</span>
                          {String(p.brand ?? "—")}
                        </td>
                        <td>
                          <span className="cs-cell-label">Inspections</span>
                          {String(p.count)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Panel>
            <Panel title="Storage and AI usage">
              {st && (
                <>
                  <div className="flex justify-between" style={{ fontSize: 13.5 }}>
                    <span>Database storage (Atlas free tier)</span>
                    <strong>
                      {used.toFixed(1)} / {st.limit_mb} MB
                    </strong>
                  </div>
                  <div
                    className="h-2.5 rounded-full mt-1.5"
                    style={{ background: "#EEEBE0" }}
                    role="progressbar"
                    aria-valuenow={used}
                    aria-valuemax={st.limit_mb}
                    aria-label="Storage used"
                  >
                    <div
                      className="h-2.5 rounded-full"
                      style={{
                        width: `${Math.min(100, (used / st.limit_mb) * 100)}%`,
                        background: used / st.limit_mb > 0.8 ? "#C07A1A" : SERIES_COLOR,
                      }}
                    />
                  </div>
                  {used / st.limit_mb > 0.8 && (
                    <div className="mt-3">
                      <Notice tone="warn" icon="alert">
                        Storage is above 80%. Upgrade the Atlas cluster or remove old data.
                      </Notice>
                    </div>
                  )}
                  <table className="cs-table mt-3">
                    <thead>
                      <tr>
                        <th>Files</th>
                        <th>Count</th>
                        <th>Size</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(st.buckets).map(([k, v]) => (
                        <tr key={k}>
                          <td>
                            {{
                              photos: "Temporary photos",
                              reports: "Report PDFs",
                              refimages: "Reference images",
                              siteimages: "Website images",
                            }[k] ?? k}
                          </td>
                          <td>
                            <span className="cs-cell-label">Count</span>
                            {v.files}
                          </td>
                          <td>
                            <span className="cs-cell-label">Size</span>
                            {v.mb} MB
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
              <p className="mb-0" style={{ fontSize: 13.5 }}>
                AI requests today: <strong>{a.ai_calls.today}</strong> · last 7 days: <strong>{a.ai_calls.last_7_days}</strong>
              </p>
            </Panel>
          </div>
        </>
      )}
    </>
  );
}

const SERIES_COLOR = "#56703A";
