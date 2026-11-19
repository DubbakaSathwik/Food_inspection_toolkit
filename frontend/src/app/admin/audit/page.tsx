"use client";

import { Fragment, useCallback, useEffect, useState } from "react";
import { PageHeader } from "@/components/shell";
import { Button, Chip, Empty, ErrorBox, fmtDate, LoadingBlock, Notice, Panel, SearchBox, SelectField, TextField } from "@/components/ui";
import { api, apiBlob, errorMessage, type Page, type S } from "@/lib/api";

type Log = S["AuditOut"];
const ACTIONS = [
  ["", "All actions"],
  ["reference.", "Reference records"],
  ["rule.", "Compliance rules"],
  ["proposal.", "Proposals"],
  ["user.", "Users & roles"],
  ["settings.", "Settings"],
  ["storage.", "Storage"],
];

export default function AuditLogs() {
  const [q, setQ] = useState("");
  const [action, setAction] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<Log> | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const query = useCallback(
    () => ({
      q,
      action: action.replace(/\.$/, "") || undefined,
      date_from: from ? new Date(from).toISOString() : undefined,
      date_to: to ? new Date(`${to}T23:59:59`).toISOString() : undefined,
    }),
    [q, action, from, to],
  );
  useEffect(() => {
    const t = window.setTimeout(
      () =>
        api<Page<Log>>("/api/v1/admin/audit", { query: { ...query(), page, page_size: 25 } })
          .then(setData)
          .catch((e) => setErr(errorMessage(e))),
      250,
    );
    return () => window.clearTimeout(t);
  }, [query, page]);
  async function exportCsv() {
    setBusy(true);
    try {
      const url = URL.createObjectURL(await apiBlob("/api/v1/admin/audit/export", { query: query() }));
      const a = document.createElement("a");
      a.href = url;
      a.download = "audit-log.csv";
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 5000);
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;
  return (
    <>
      <PageHeader
        title="Audit Logs"
        subtitle="Every administrative change: who, what, when and which fields changed."
        actions={
          <Button variant="secondary" icon="download" working={busy} onClick={() => void exportCsv()}>
            Export CSV
          </Button>
        }
      />
      <Notice icon="lock">The audit log is read-only. Entries cannot be edited or deleted from the application.</Notice>
      {err && <ErrorBox error={err} />}
      <Panel>
        <div className="flex flex-wrap items-end gap-3 mb-4">
          <div className="flex-[1_1_220px] max-w-[300px]">
            <SearchBox
              value={q}
              onChange={(v) => {
                setQ(v);
                setPage(1);
              }}
              placeholder="Actor, record or summary"
            />
          </div>
          <SelectField
            label="Action"
            value={action}
            onChange={(e) => {
              setAction(e.target.value);
              setPage(1);
            }}
            className="w-[190px]"
          >
            {ACTIONS.map(([k, l]) => (
              <option key={k} value={k}>
                {l}
              </option>
            ))}
          </SelectField>
          <TextField
            label="From"
            type="date"
            value={from}
            onChange={(e) => {
              setFrom(e.target.value);
              setPage(1);
            }}
            className="w-[160px]"
          />
          <TextField
            label="To"
            type="date"
            value={to}
            onChange={(e) => {
              setTo(e.target.value);
              setPage(1);
            }}
            className="w-[160px]"
          />
        </div>
        {!data ? (
          <LoadingBlock rows={8} />
        ) : data.items.length === 0 ? (
          <Empty icon="logs" title="No entries match" />
        ) : (
          <table className="cs-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Actor</th>
                <th>Action</th>
                <th>Record</th>
                <th>Summary</th>
                <th>Changes</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((l) => {
                const n = Object.keys(l.changes).length;
                return (
                  <Fragment key={l.id}>
                    <tr>
                      <td>
                        <span className="cs-cell-label">Time</span>
                        <span style={{ whiteSpace: "nowrap" }}>{fmtDate(l.at, true)}</span>
                      </td>
                      <td>
                        <span className="cs-cell-label">Actor</span>
                        <strong>{l.actor_name}</strong>
                        <div style={{ fontSize: 12, color: "#686B60" }}>{l.actor_role?.replace("_", " ")}</div>
                      </td>
                      <td>
                        <Chip tone="neu" dot={false}>
                          {l.action}
                        </Chip>
                      </td>
                      <td>
                        <span className="cs-cell-label">Record</span>
                        <span style={{ fontSize: 13 }}>
                          {l.target_type} · {l.target_id}
                        </span>
                      </td>
                      <td>
                        <span className="cs-cell-label">Summary</span>
                        {l.summary || "—"}
                      </td>
                      <td>
                        {n ? (
                          <Button
                            small
                            variant="secondary"
                            aria-expanded={open === l.id}
                            onClick={() => setOpen(open === l.id ? null : l.id)}
                          >
                            {n} field{n > 1 ? "s" : ""}
                          </Button>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                    {open === l.id && (
                      <tr>
                        <td colSpan={6} style={{ background: "#FBF8F0" }}>
                          <table className="w-full" style={{ fontSize: 13 }}>
                            <thead>
                              <tr>
                                <th className="text-left">Field</th>
                                <th className="text-left">Before</th>
                                <th className="text-left">After</th>
                              </tr>
                            </thead>
                            <tbody>
                              {Object.entries(l.changes).map(([k, v]) => {
                                const [b, a] = Array.isArray(v) ? v : [null, v];
                                return (
                                  <tr key={k}>
                                    <td className="pr-3 align-top font-semibold">{k}</td>
                                    <td className="pr-3 align-top" style={{ overflowWrap: "anywhere" }}>
                                      {JSON.stringify(b)}
                                    </td>
                                    <td className="align-top" style={{ overflowWrap: "anywhere" }}>
                                      {JSON.stringify(a)}
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        )}
        <div className="flex items-center justify-between gap-3 mt-4">
          <span style={{ fontSize: 13, color: "#55584E" }}>{data ? `${data.total} entries` : ""}</span>
          <div className="flex items-center gap-2">
            <Button small variant="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>
              Previous
            </Button>
            <span style={{ fontSize: 13 }}>
              Page {page} of {pages}
            </span>
            <Button small variant="secondary" disabled={page >= pages} onClick={() => setPage(page + 1)}>
              Next
            </Button>
          </div>
        </div>
      </Panel>
    </>
  );
}
