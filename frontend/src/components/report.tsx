"use client";

import type { ReactNode } from "react";
import type { Inspection } from "@/lib/api";
import { AuthImage } from "./media";
import { CATEGORY_LABELS, fmtDate, label, Logo } from "./ui";

export const REPORT_SECTIONS = [
  "Inspection ID, date and time",
  "Inspector details",
  "Product and manufacturer details",
  "Original product photographs",
  "Complete extracted label information",
  "FSSAI licence verification (demo records)",
  "Manufacturer and reference database matching",
  "FSSAI compliance findings and rule evidence",
  "Packaging anomaly and suspicious-claim analysis",
  "AI confidence indicators",
  "Inspector corrections and comments",
  "Final inspector decision and remarks",
  "Sources, limitations and disclaimers",
];

type A = {
  reference?: { status: string; detail: string; comparisons?: { field: string; extracted: string; reference: string; result: string }[] };
  licence?: { label: string; detail: string };
  packaging?: { summary: string; observations: { area: string; observation: string; severity: string }[] };
  compliance?: {
    results: {
      rule_code: string;
      version: number;
      requirement: string;
      result: string;
      reason: string;
      reference: string;
      claim: boolean;
      title: string;
    }[];
  };
};

function KV({ rows }: { rows: [string, ReactNode][] }) {
  return (
    <table className="w-full border-collapse" style={{ fontSize: 11.5 }}>
      <tbody>
        {rows.map(([k, v]) => (
          <tr key={k}>
            <th
              scope="row"
              className="text-left align-top"
              style={{ width: "36%", padding: "5px 8px", border: "1px solid #DCDACB", background: "#F7F5EC", fontWeight: 700 }}
            >
              {k}
            </th>
            <td style={{ padding: "5px 8px", border: "1px solid #DCDACB", overflowWrap: "anywhere" }}>{v ?? "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Grid({ head, rows }: { head: string[]; rows: ReactNode[][] }) {
  return (
    <table className="w-full border-collapse" style={{ fontSize: 11 }}>
      <thead>
        <tr>
          {head.map((h) => (
            <th key={h} className="text-left" style={{ padding: "5px 8px", border: "1px solid #DCDACB", background: "#EEF2E1" }}>
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            {r.map((c, j) => (
              <td key={j} style={{ padding: "5px 8px", border: "1px solid #DCDACB", verticalAlign: "top", overflowWrap: "anywhere" }}>
                {c ?? "—"}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function H({ n }: { n: number }) {
  return (
    <h3
      style={{
        margin: "18px 0 8px",
        fontSize: 12,
        fontWeight: 800,
        letterSpacing: 0.6,
        textTransform: "uppercase",
        borderBottom: "2px solid #20231D",
        paddingBottom: 4,
      }}
    >
      {n}. {REPORT_SECTIONS[n - 1]}
    </h3>
  );
}

/** HTML rendition of the PDF (same 13 sections, same order) used for the on-screen preview. */
export function ReportDocument({ d, signature, view }: { d: Inspection; signature: string; view: "print" | "mobile" }) {
  const a = (d.analysis ?? {}) as A;
  const f = Object.fromEntries(d.fields.map((x) => [x.key, x]));
  const v = (k: string) => f[k]?.value ?? null;
  const comp = a.compliance?.results ?? [];
  const corrections = d.fields.filter((x) => x.status === "edited");
  const decisions = d.findings.filter((x) => x.decision);
  return (
    <article
      aria-label="Report preview"
      className="bg-white mx-auto"
      style={{
        maxWidth: view === "print" ? 620 : 420,
        padding: view === "print" ? "36px 40px" : "20px 18px",
        boxShadow: "0 8px 24px rgba(40,40,30,.12)",
        color: "#20231D",
        fontFamily: "Helvetica, Arial, sans-serif",
      }}
    >
      <header className="flex items-start justify-between gap-3 pb-3" style={{ borderBottom: "3px double #20231D" }}>
        <div>
          <div style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: 1.4, color: "#56703A" }}>CRATE-SCAN</div>
          <div style={{ fontSize: view === "print" ? 18 : 15, fontWeight: 800 }}>FOOD PRODUCT INSPECTION REPORT</div>
          <div style={{ fontSize: 10, color: "#55584E" }}>
            Decision-support report · demo reference data · not an official FSSAI document
          </div>
        </div>
        <span className="max-[480px]:hidden">
          <Logo size={30} text={0} />
        </span>
      </header>
      <H n={1} />
      <KV
        rows={[
          ["Inspection ID", d.id],
          ["Created", fmtDate(d.created_at, true)],
          ["Category", d.category ? CATEGORY_LABELS[d.category] : "—"],
        ]}
      />
      <H n={2} />
      <KV rows={[["Inspector", d.owner_name || "—"]]} />
      <H n={3} />
      <KV
        rows={[
          ["Product", v("product_name")],
          ["Brand", v("brand")],
          ["Net quantity", v("net_quantity")],
          ["Manufacturer", v("manufacturer_name")],
          ["Address", v("manufacturer_address")],
          ["FSSAI licence (as printed)", v("fssai_licence")],
        ]}
      />
      <H n={4} />
      <div className="grid grid-cols-3 gap-2 max-[480px]:grid-cols-2">
        {d.photos.map((p, i) => (
          <figure key={p.id} className="m-0">
            <div className="overflow-hidden" style={{ height: 96, background: "#ECE9DE" }}>
              <AuthImage path={d.photos_deleted ? null : `/api/v1/inspections/${d.id}/photos/${p.id}?thumb=true`} alt={`Photo ${i + 1}`} />
            </div>
            <figcaption style={{ fontSize: 9.5, color: "#55584E", textAlign: "center" }}>
              Photo {i + 1} · {label(p.label)}
            </figcaption>
          </figure>
        ))}
      </div>
      {d.photos_deleted && (
        <p style={{ fontSize: 10, color: "#55584E" }}>
          Originals were deleted after the PDF was generated; the PDF holds the embedded copies.
        </p>
      )}
      <H n={5} />
      <Grid
        head={["Field", "Value", "Photo"]}
        rows={d.fields.map((x) => [x.label, x.value ?? "Not present on pack", x.source_photo ? `Photo ${x.source_photo}` : "—"])}
      />
      <H n={6} />
      <KV
        rows={[
          ["Result", a.licence?.label],
          ["Detail", a.licence?.detail],
          ["Note", "Demonstration data — not government verification"],
        ]}
      />
      <H n={7} />
      <p style={{ fontSize: 11, margin: "0 0 6px" }}>
        {label(a.reference?.status)} — {a.reference?.detail}
      </p>
      {a.reference?.comparisons?.length ? (
        <Grid
          head={["Field", "On pack", "Reference (demo)", "Result"]}
          rows={a.reference.comparisons.map((r) => [r.field, r.extracted, r.reference, r.result])}
        />
      ) : null}
      <H n={8} />
      <Grid
        head={["Rule", "Requirement", "Result", "Reason"]}
        rows={comp.map((r) => [`${r.rule_code} v${r.version}`, r.requirement, r.result.replace("_", " "), r.reason || "—"])}
      />
      <H n={9} />
      <p style={{ fontSize: 11, margin: "0 0 6px" }}>{a.packaging?.summary}</p>
      <Grid
        head={["Area", "Observation", "Severity"]}
        rows={[
          ...(a.packaging?.observations ?? []).map((o) => [o.area, o.observation, o.severity]),
          ...comp.filter((r) => r.claim && r.result === "review").map((r) => [`Claim — ${r.title}`, r.reason, "review"]),
        ]}
      />
      <H n={10} />
      <Grid
        head={["Field", "AI value", "Confidence"]}
        rows={d.fields.map((x) => [x.label, x.ai_value ?? "—", `${x.confidence_level} (${(x.ai_confidence ?? 0).toFixed(2)})`])}
      />
      <H n={11} />
      {corrections.length || decisions.length ? (
        <Grid
          head={["Item", "Original (AI)", "Inspector"]}
          rows={[
            ...corrections.map((x) => [x.label, x.ai_value ?? "—", x.value ?? "Not present"]),
            ...decisions.map((x) => [
              x.title,
              x.ai_original ?? x.extracted ?? "—",
              `${x.decision!.action}${x.decision!.corrected_value ? `: ${x.decision!.corrected_value}` : ""}${x.decision!.note ? ` — ${x.decision!.note}` : ""}`,
            ]),
          ]}
        />
      ) : (
        <p style={{ fontSize: 11 }}>No corrections recorded.</p>
      )}
      <H n={12} />
      <KV
        rows={[
          ["Final classification (inspector)", label(d.decision?.classification)],
          ["Suggested (provisional)", label(d.suggestion?.classification)],
          ["Remarks", d.decision?.remarks || "—"],
          ["Typed signature", `${signature || "—"} (typed name — not a certified digital signature)`],
        ]}
      />
      <H n={13} />
      <ul style={{ fontSize: 10.5, lineHeight: 1.5, paddingLeft: 16, color: "#3a3d35" }}>
        <li>Reference, licence and rule data are fictional demonstration records maintained by administrators.</li>
        <li>A demo licence match is not government verification. A missing reference record does not mean the product is fake.</li>
        <li>Packaging differences are observations, not proof of counterfeiting. AI confidence is not measured accuracy.</li>
        <li>Official sources: FSSAI (fssai.gov.in), FoSCoS (foscos.fssai.gov.in).</li>
      </ul>
    </article>
  );
}
