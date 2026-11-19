"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icon";
import { PageHeader } from "@/components/shell";
import {
  Button,
  ButtonLink,
  CATEGORY_LABELS,
  Chip,
  Empty,
  ErrorBox,
  fmtDate,
  IconButton,
  LoadingBlock,
  Panel,
  SearchBox,
  SelectField,
  TextField,
} from "@/components/ui";
import { api, apiBlob, errorMessage, type InspectionSummary, type Page } from "@/lib/api";
import { nextStep } from "@/lib/inspection";

const FILTERS = [
  ["", "All"],
  ["verified", "Verified"],
  ["not_verified", "Not verified"],
  ["suspicious", "Suspicious"],
] as const;

async function saveBlob(path: string, name: string, query?: Record<string, string>) {
  const url = URL.createObjectURL(await apiBlob(path, { query }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

export default function HistoryPage() {
  const [q, setQ] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [category, setCategory] = useState("");
  const [cls, setCls] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page<InspectionSummary> | null>(null);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const query = useCallback(
    (extra: Record<string, string | number> = {}) => ({
      q,
      category,
      date_from: from ? new Date(from).toISOString() : "",
      date_to: to ? new Date(`${to}T23:59:59`).toISOString() : "",
      ...extra,
    }),
    [q, category, from, to],
  );

  useEffect(() => {
    const t = window.setTimeout(() => {
      setErr(null);
      api<Page<InspectionSummary>>("/api/v1/inspections", { query: { ...query(), classification: cls, page, page_size: 20 } })
        .then(setData)
        .catch((e) => setErr(errorMessage(e)));
      Promise.all(
        FILTERS.map(([k]) =>
          api<Page<InspectionSummary>>("/api/v1/inspections", { query: { ...query(), classification: k, page_size: 1 } }).then(
            (p) => [k, p.total] as const,
          ),
        ),
      )
        .then((r) => setCounts(Object.fromEntries(r)))
        .catch(() => undefined);
    }, 250);
    return () => window.clearTimeout(t);
  }, [query, cls, page]);

  async function exportAs(format: "csv" | "xlsx") {
    setBusy(format);
    try {
      const qs = Object.fromEntries(Object.entries({ ...query(), classification: cls, format }).filter(([, v]) => v !== "")) as Record<
        string,
        string
      >;
      await saveBlob("/api/v1/inspections/export", `inspection-history.${format}`, qs);
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(null);
    }
  }

  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;
  return (
    <>
      <PageHeader
        title="Inspection History"
        subtitle="Your own inspections. Search, filter and re-open any past report."
        actions={
          <ButtonLink href="/inspector/new" iconRight="plus">
            New Inspection
          </ButtonLink>
        }
      />
      {err && <ErrorBox error={err} />}
      <Panel>
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex-[2_1_240px] min-w-0">
            <SearchBox
              value={q}
              onChange={(v) => {
                setQ(v);
                setPage(1);
              }}
              placeholder="Product, brand or inspection ID"
            />
          </div>
          <TextField
            label="From"
            type="date"
            value={from}
            onChange={(e) => {
              setFrom(e.target.value);
              setPage(1);
            }}
            className="flex-[1_1_140px]"
          />
          <TextField
            label="To"
            type="date"
            value={to}
            onChange={(e) => {
              setTo(e.target.value);
              setPage(1);
            }}
            className="flex-[1_1_140px]"
          />
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
        </div>
        <div className="flex flex-wrap gap-2 mt-4 pb-4 border-b border-line" role="group" aria-label="Classification filter">
          {FILTERS.map(([k, l]) => (
            <button
              key={k}
              type="button"
              className="cs-chipbtn"
              aria-pressed={cls === k}
              onClick={() => {
                setCls(k);
                setPage(1);
              }}
            >
              {l}{" "}
              <span className="cs-chip tone-tint" style={{ padding: "0 6px", fontSize: 11 }}>
                {counts[k] ?? "·"}
              </span>
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 my-4 cs-bar">
          <span style={{ fontSize: 13.5, fontWeight: 600, color: "#55584E" }}>
            {data ? `Showing ${data.items.length} of ${data.total} inspections` : "Loading…"}
          </span>
          <div className="flex flex-wrap gap-2.5 cs-pbtns">
            <Button small variant="secondary" icon="sheet" working={busy === "xlsx"} onClick={() => void exportAs("xlsx")}>
              Export Excel
            </Button>
            <Button small variant="secondary" icon="file" working={busy === "csv"} onClick={() => void exportAs("csv")}>
              Export CSV
            </Button>
          </div>
        </div>
        {!data ? (
          <LoadingBlock rows={6} />
        ) : data.items.length === 0 ? (
          <Empty icon="search" title="No inspections match these filters">
            Try clearing the search or date range.
          </Empty>
        ) : (
          <table className="cs-table">
            <thead>
              <tr>
                <th>Inspection ID</th>
                <th>Product</th>
                <th>Brand</th>
                <th>Category</th>
                <th>Date</th>
                <th>Classification</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((i) => {
                const s = nextStep(i);
                return (
                  <tr key={i.id}>
                    <td>
                      <span className="cs-cell-label">Inspection ID</span>
                      <span style={{ fontSize: 13, fontWeight: 600, color: "#686B60" }}>{i.id}</span>
                    </td>
                    <td>
                      <span className="cs-cell-label">Product</span>
                      <strong>{i.product_name || "Untitled product"}</strong>
                    </td>
                    <td>
                      <span className="cs-cell-label">Brand</span>
                      {i.brand ?? "—"}
                    </td>
                    <td>
                      <span className="cs-cell-label">Category</span>
                      {i.category ? CATEGORY_LABELS[i.category] : "—"}
                    </td>
                    <td>
                      <span className="cs-cell-label">Date</span>
                      {fmtDate(i.created_at)}
                    </td>
                    <td>
                      <span className="cs-cell-label">Classification</span>
                      {i.classification ? <Chip status={i.classification} /> : <Chip tone={s.tone}>{s.badge}</Chip>}
                    </td>
                    <td>
                      <div className="flex gap-2">
                        <Link href={s.href} className="cs-ib" aria-label={`Open ${i.id}`} title="Open">
                          <Icon name="eye" size={17} />
                        </Link>
                        {i.has_report && (
                          <IconButton
                            icon="download"
                            label={`Download report ${i.id}`}
                            onClick={() =>
                              void saveBlob(`/api/v1/inspections/${i.id}/report.pdf`, `${i.id}.pdf`, { download: "true" }).catch((e) =>
                                setErr(errorMessage(e)),
                              )
                            }
                          />
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
        {pages > 1 && (
          <div className="flex items-center justify-end gap-2 mt-4">
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
        )}
      </Panel>
      <Panel title="Follow-up notes">
        <p className="m-0" style={{ fontSize: 13.5, color: "#55584E" }}>
          Notes added to a past inspection are stored separately and never change the original findings or the saved report. Open a
          completed inspection to read or add its notes.
        </p>
      </Panel>
    </>
  );
}
