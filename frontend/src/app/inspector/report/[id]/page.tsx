"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Icon } from "@/components/icon";
import { AIWorkingOverlay, Stepper } from "@/components/inspection";
import { REPORT_SECTIONS, ReportDocument } from "@/components/report";
import { PageHeader } from "@/components/shell";
import {
  Backlink,
  Button,
  Chip,
  ErrorBox,
  fmtDate,
  LoadingBlock,
  Modal,
  Notice,
  Panel,
  Pill,
  SelectField,
  TextArea,
  TextField,
} from "@/components/ui";
import { ApiError, api, apiBlob, errorMessage, type Inspection, type Proposal } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { me } = useAuth();
  const [d, setD] = useState<Inspection | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [view, setView] = useState<"print" | "mobile">(() =>
    typeof window !== "undefined" && window.matchMedia("(max-width: 760px)").matches ? "mobile" : "print",
  );
  const [signature, setSignature] = useState(() => me?.name ?? "");
  const [reviewed, setReviewed] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [propOpen, setPropOpen] = useState(false);

  useEffect(() => {
    api<Inspection>(`/api/v1/inspections/${id}`)
      .then((x) => {
        if (x.status !== "completed" && !x.decision) router.replace(`/inspector/findings/${id}`);
        setD(x);
        if (x.report?.signature_name) setSignature(x.report.signature_name);
      })
      .catch((e) => setErr(errorMessage(e)));
  }, [id, router]);

  const done = d?.status === "completed";

  async function generate() {
    setErr(null);
    setGenerating(true);
    try {
      setD(
        await api<Inspection>(`/api/v1/inspections/${id}/report`, {
          method: "POST",
          body: { signature_name: signature, confirm_reviewed: reviewed },
        }),
      );
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setGenerating(false);
    }
  }
  async function pdf(): Promise<Blob> {
    return apiBlob(`/api/v1/inspections/${id}/report.pdf`);
  }
  async function download() {
    setBusy("download");
    try {
      const url = URL.createObjectURL(await pdf());
      const a = document.createElement("a");
      a.href = url;
      a.download = `${id}.pdf`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 5000);
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(null);
    }
  }
  async function print() {
    setBusy("print");
    try {
      const url = URL.createObjectURL(await pdf());
      const w = window.open(url, "_blank", "noopener");
      if (!w) window.location.href = url;
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(null);
    }
  }
  async function share() {
    setBusy("share");
    try {
      const file = new File([await pdf()], `${id}.pdf`, { type: "application/pdf" });
      const nav = navigator as Navigator & { canShare?: (d: ShareData) => boolean };
      if (nav.canShare?.({ files: [file] })) await nav.share({ files: [file], title: `Inspection report ${id}` });
      else await download();
    } catch (e) {
      if ((e as Error).name !== "AbortError") setErr(errorMessage(e));
    } finally {
      setBusy(null);
    }
  }
  async function addNote() {
    if (!note.trim()) return;
    setBusy("note");
    try {
      const n = await api<{ id: string; text: string; created_at: string }>(`/api/v1/inspections/${id}/notes`, {
        method: "POST",
        body: { text: note.trim() },
      });
      setD((x) => (x ? { ...x, notes: [...x.notes, n] } : x));
      setNote("");
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(null);
    }
  }

  if (!d)
    return (
      <>
        <PageHeader title="Report Preview" />
        {err ? (
          <ErrorBox error={err} />
        ) : (
          <Panel>
            <LoadingBlock rows={6} />
          </Panel>
        )}
      </>
    );
  const refStatus = ((d.analysis ?? {}) as { reference?: { status?: string } }).reference?.status;
  const actions = (
    <div className="flex flex-wrap items-center gap-2.5 cs-pbtns">
      <Button variant="secondary" icon="download" disabled={!done} working={busy === "download"} onClick={() => void download()}>
        Download PDF
      </Button>
      <Button variant="secondary" icon="printer" disabled={!done} working={busy === "print"} onClick={() => void print()}>
        Print
      </Button>
      <Button variant="secondary" icon="share" disabled={!done} working={busy === "share"} onClick={() => void share()}>
        Share
      </Button>
      <Button
        variant="secondary"
        icon="eye"
        onClick={() => setView(view === "print" ? "mobile" : "print")}
        aria-pressed={view === "mobile"}
      >
        View: {view === "print" ? "Print" : "Mobile"}
      </Button>
    </div>
  );
  return (
    <>
      <AIWorkingOverlay
        title="Generating the PDF report"
        active={generating}
        steps={[
          "Collecting approved values and findings",
          "Embedding compressed photographs",
          "Writing the 13 report sections",
          "Saving the report and removing originals",
        ]}
      />
      <PageHeader
        title={done ? "Inspection Report" : "Report Preview"}
        back={
          <Backlink href={done ? "/inspector/history" : `/inspector/findings/${id}`}>
            {done ? "Back to history" : "Back to findings"}
          </Backlink>
        }
        subtitle={
          done
            ? `Saved ${fmtDate(d.report?.generated_at, true)} · ${d.report?.pages ?? "—"} pages. Original findings are locked; add follow-up notes below.`
            : "Check the report before saving. Saving locks the original findings; later notes are added separately."
        }
        actions={<Pill>Step 5 of 5</Pill>}
      />
      <Stepper current={5} />
      {err && <ErrorBox error={err} />}
      <div className="cs-panel flex flex-wrap items-center justify-between gap-3" style={{ padding: 14 }}>
        {actions}
        {done ? <Chip status="completed">Report saved</Chip> : null}
      </div>

      <div className="grid grid-cols-[minmax(0,1fr)_300px] gap-5 items-start max-[960px]:grid-cols-1">
        <div className="rounded-[12px] p-6 max-[760px]:p-2 min-w-0" style={{ background: "#E8E5DA" }}>
          <ReportDocument d={d} signature={signature} view={view} />
        </div>
        <div className="flex flex-col gap-5">
          <aside className="cs-panel" aria-label="Report contents">
            <h2 style={{ margin: "0 0 10px", fontSize: 16, fontWeight: 700 }}>Report contents</h2>
            <ol className="list-none m-0 p-0 flex flex-col gap-1.5" style={{ fontSize: 13.5 }}>
              {REPORT_SECTIONS.map((s, i) => (
                <li key={s} className="flex gap-2">
                  <Icon name="check" size={15} color="#56703A" />
                  {i + 1}. {s}
                </li>
              ))}
            </ol>
          </aside>
          {!done ? (
            <aside className="cs-panel flex flex-col gap-3" aria-label="Signature">
              <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Signature</h2>
              <TextField
                label="Typed inspector name"
                value={signature}
                onChange={(e) => setSignature(e.target.value)}
                maxLength={200}
                hint="Shown on the report as a typed signature. It is not a certified digital signature."
              />
              <label className="flex gap-2 items-start" style={{ fontSize: 13.5 }}>
                <input
                  type="checkbox"
                  checked={reviewed}
                  onChange={(e) => setReviewed(e.target.checked)}
                  className="mt-1 accent-[#3E5228]"
                />
                I have reviewed the findings and my decision ({d.decision ? d.decision.classification.replace("_", " ") : "—"}).
              </label>
              <Button icon="check" disabled={signature.trim().length < 2 || !reviewed} working={generating} onClick={() => void generate()}>
                Save Report
              </Button>
              <p className="m-0" style={{ fontSize: 12.5, color: "#686B60" }}>
                Saving deletes the original photographs; compressed copies stay embedded in the PDF.
              </p>
            </aside>
          ) : (
            <aside className="cs-panel flex flex-col gap-3" aria-label="Follow-up notes">
              <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Follow-up notes</h2>
              {d.notes.length === 0 && (
                <p className="m-0" style={{ fontSize: 13, color: "#686B60" }}>
                  Notes never change the original findings.
                </p>
              )}
              {d.notes.map((n) => (
                <div key={n.id} className="rounded-[8px] p-2.5" style={{ background: "#FBF8F0", fontSize: 13.5 }}>
                  {n.text}
                  <div style={{ fontSize: 11.5, color: "#686B60" }}>{fmtDate(n.created_at, true)}</div>
                </div>
              ))}
              <TextArea label="Add a note" value={note} onChange={(e) => setNote(e.target.value)} maxLength={8000} />
              <Button small variant="secondary" working={busy === "note"} disabled={!note.trim()} onClick={() => void addNote()}>
                Add note
              </Button>
            </aside>
          )}
          <aside className="cs-panel flex flex-col gap-3" aria-label="Submit this product">
            <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>Submit this product?</h2>
            {d.proposal_id ? (
              <p className="m-0" style={{ fontSize: 13.5, color: "#55584E" }}>
                Proposal <strong>{d.proposal_id}</strong> was submitted. <Link href="/inspector/proposals">Track its status</Link>.
              </p>
            ) : (
              <>
                <p className="m-0" style={{ fontSize: 13.5, color: "#55584E", lineHeight: 1.55 }}>
                  {refStatus === "exact"
                    ? "This product matched an existing reference record, so a proposal is usually not needed."
                    : "When a product is missing from the demo reference database you can submit it here with this report attached."}
                </p>
                <Button variant="secondary" icon="proposal" disabled={!done} onClick={() => setPropOpen(true)}>
                  Submit as proposal
                </Button>
                {!done && <span style={{ fontSize: 12.5, color: "#686B60" }}>Available after the report is saved.</span>}
              </>
            )}
          </aside>
        </div>
      </div>
      <ProposalDialog
        open={propOpen}
        d={d}
        onClose={() => setPropOpen(false)}
        onDone={(p) => {
          setD({ ...d, proposal_id: p.id });
          setPropOpen(false);
        }}
      />
    </>
  );
}

function ProposalDialog({
  open,
  d,
  onClose,
  onDone,
}: {
  open: boolean;
  d: Inspection;
  onClose: () => void;
  onDone: (p: Proposal) => void;
}) {
  const v = (k: string) => d.fields.find((x) => x.key === k)?.value ?? "";
  const [form, setForm] = useState(() => ({
    product_name: v("product_name"),
    brand: v("brand"),
    variant: v("variant"),
    category: d.category ?? "staples",
    net_quantity: v("net_quantity"),
    gtin: v("barcode").replace(/\D/g, "").slice(0, 14),
    manufacturer_name: v("manufacturer_name"),
    manufacturer_address: v("manufacturer_address"),
    fssai_licence: v("fssai_licence").replace(/\D/g, ""),
  }));
  const [remarks, setRemarks] = useState("");
  const [fieldErr, setFieldErr] = useState<Record<string, string>>({});
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });
  async function submit() {
    setBusy(true);
    setErr(null);
    setFieldErr({});
    try {
      onDone(await api<Proposal>("/api/v1/proposals", { method: "POST", body: { inspection_id: d.id, product: form, remarks } }));
    } catch (e) {
      if (e instanceof ApiError && e.fields)
        setFieldErr(Object.fromEntries(Object.entries(e.fields).map(([k, m]) => [k.replace("product.", ""), m])));
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      open={open}
      title="Submit product proposal"
      onClose={onClose}
      wide
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button working={busy} onClick={() => void submit()}>
            Submit proposal
          </Button>
        </>
      }
    >
      <Notice>
        Approval adds the product to the demo reference database only — it is not FSSAI certification. Your report PDF is attached.
      </Notice>
      {err && (
        <div className="mt-3">
          <ErrorBox error={err} />
        </div>
      )}
      <div className="mt-4 grid grid-cols-2 gap-3 max-[760px]:grid-cols-1">
        <TextField label="Product name" value={form.product_name} onChange={set("product_name")} error={fieldErr.product_name} required />
        <TextField label="Brand" value={form.brand} onChange={set("brand")} error={fieldErr.brand} required />
        <TextField label="Variant" value={form.variant} onChange={set("variant")} />
        <SelectField label="Category" value={form.category} onChange={set("category")}>
          <option value="beverages">Packaged beverages & water</option>
          <option value="snacks">Packaged snacks</option>
          <option value="dairy">Dairy products</option>
          <option value="staples">Groceries & food staples</option>
        </SelectField>
        <TextField label="Net quantity" value={form.net_quantity} onChange={set("net_quantity")} />
        <TextField label="Barcode / GTIN" value={form.gtin} onChange={set("gtin")} error={fieldErr.gtin} inputMode="numeric" />
        <TextField label="Manufacturer" value={form.manufacturer_name} onChange={set("manufacturer_name")} />
        <TextField
          label="FSSAI licence no."
          value={form.fssai_licence}
          onChange={set("fssai_licence")}
          error={fieldErr.fssai_licence}
          inputMode="numeric"
        />
        <TextArea
          className="col-span-2 max-[760px]:col-span-1"
          label="Manufacturer address"
          value={form.manufacturer_address}
          onChange={set("manufacturer_address")}
        />
        <TextArea
          className="col-span-2 max-[760px]:col-span-1"
          label="Remarks for the administrator"
          value={remarks}
          onChange={(e) => setRemarks(e.target.value)}
        />
      </div>
    </Modal>
  );
}
