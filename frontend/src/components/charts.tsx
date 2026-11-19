"use client";

import { useState } from "react";

/* Chart rules (dataviz skill): single-series magnitude = one hue; thin marks with 4px rounded ends; values in
   text ink; per-mark hover tooltip; every chart has a table alternative; status-like composition carries labels. */

export const SERIES = "#56703A";
export const CLASS_COLORS: Record<string, string> = { verified: "#4E7A2A", not_verified: "#5F7C99", suspicious: "#C07A1A" };

export function HBarList({ rows, label: lbl }: { rows: { label: string; value: number }[]; label: string }) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  return (
    <ul className="list-none m-0 p-0 flex flex-col gap-3.5" aria-label={lbl}>
      {rows.map((r) => (
        <li key={r.label} title={`${r.label}: ${r.value}`}>
          <div className="flex justify-between gap-3" style={{ fontSize: 13.5 }}>
            <span>{r.label}</span>
            <strong>{r.value}</strong>
          </div>
          <div className="h-2 rounded-full mt-1" style={{ background: "#EEEBE0" }}>
            <div
              className="h-2 rounded-full"
              style={{ width: `${(r.value / max) * 100}%`, minWidth: r.value ? 4 : 0, background: SERIES }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}

export function ColumnChart({
  data,
  label: lbl,
  height = 180,
}: {
  data: { label: string; value: number }[];
  label: string;
  height?: number;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const [table, setTable] = useState(false);
  const max = Math.max(1, ...data.map((d) => d.value));
  if (table) {
    return (
      <div>
        <button type="button" className="cs-chipbtn mb-2" onClick={() => setTable(false)}>
          Show chart
        </button>
        <table className="cs-table">
          <thead>
            <tr>
              <th>Period</th>
              <th>{lbl}</th>
            </tr>
          </thead>
          <tbody>
            {data.map((d) => (
              <tr key={d.label}>
                <td>{d.label}</td>
                <td>{d.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
  return (
    <div>
      <div className="flex justify-end">
        <button type="button" className="cs-chipbtn" onClick={() => setTable(true)}>
          Show table
        </button>
      </div>
      <div
        role="img"
        aria-label={`${lbl}: ${data.map((d) => `${d.label} ${d.value}`).join(", ")}`}
        className="relative flex items-end gap-[2px] mt-2"
        style={{ height, borderBottom: "1px solid #D8D6C9" }}
        onMouseLeave={() => setHover(null)}
      >
        {data.map((d, i) => (
          <div key={d.label} className="relative flex-1 h-full flex flex-col justify-end items-center" onMouseEnter={() => setHover(i)}>
            {hover === i && (
              <div
                className="absolute z-10 rounded-[8px] border border-line bg-white px-2.5 py-1.5 shadow-md whitespace-nowrap pointer-events-none"
                style={{ bottom: `calc(${(d.value / max) * 100}% + 8px)`, fontSize: 12.5 }}
              >
                <strong>{d.value}</strong> · {d.label}
              </div>
            )}
            <div
              style={{
                width: "min(36px, 70%)",
                height: `${(d.value / max) * 100}%`,
                minHeight: d.value ? 3 : 0,
                background: SERIES,
                opacity: hover === null || hover === i ? 1 : 0.55,
                borderRadius: "4px 4px 0 0",
                transition: "opacity .15s",
              }}
            />
          </div>
        ))}
      </div>
      <div className="flex gap-[2px] mt-1.5">
        {data.map((d, i) => (
          <span
            key={d.label}
            className="flex-1 text-center"
            style={{ fontSize: 11, color: "#686B60", visibility: data.length > 12 && i % 2 ? "hidden" : "visible" }}
          >
            {d.label}
          </span>
        ))}
      </div>
    </div>
  );
}

export function StackedShare({ parts }: { parts: { key: string; label: string; value: number }[] }) {
  const total = parts.reduce((s, p) => s + p.value, 0);
  if (!total)
    return (
      <p className="m-0" style={{ fontSize: 13.5, color: "#686B60" }}>
        No classified inspections in this period.
      </p>
    );
  return (
    <div>
      <div
        className="flex h-5 overflow-hidden rounded-[6px] gap-[2px]"
        role="img"
        aria-label={parts.map((p) => `${p.label} ${p.value} (${Math.round((p.value / total) * 100)}%)`).join(", ")}
      >
        {parts
          .filter((p) => p.value)
          .map((p) => (
            <div
              key={p.key}
              title={`${p.label}: ${p.value}`}
              style={{ width: `${(p.value / total) * 100}%`, background: CLASS_COLORS[p.key] }}
            />
          ))}
      </div>
      <ul className="list-none m-0 mt-3 p-0 flex flex-wrap gap-x-5 gap-y-1.5" style={{ fontSize: 13 }}>
        {parts.map((p) => (
          <li key={p.key} className="flex items-center gap-1.5">
            <span aria-hidden style={{ width: 10, height: 10, borderRadius: 3, background: CLASS_COLORS[p.key] }} />
            {p.label} · {p.value} ({Math.round((p.value / total) * 100)}%)
          </li>
        ))}
      </ul>
    </div>
  );
}
