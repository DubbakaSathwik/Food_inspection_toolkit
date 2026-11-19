"use client";

import { useCallback, useEffect, useState } from "react";
import { PageHeader } from "@/components/shell";
import {
  Button,
  CATEGORY_LABELS,
  Chip,
  Empty,
  ErrorBox,
  fmtDate,
  IconButton,
  label,
  LoadingBlock,
  Metric,
  Modal,
  Notice,
  Panel,
  SearchBox,
  SelectField,
  TextArea,
  TextField,
} from "@/components/ui";
import { ApiError, api, errorMessage, type Page, type Rule, type S } from "@/lib/api";

const FIELD_OPTIONS = [
  "product_name",
  "brand",
  "variant",
  "manufacturer_name",
  "manufacturer_address",
  "fssai_licence",
  "customer_care",
  "mfg_date",
  "expiry",
  "batch",
  "net_quantity",
  "mrp",
  "selling_price",
  "ingredients",
  "nutrition",
  "allergens",
  "veg_symbol",
  "claims",
  "certifications",
  "barcode",
  "qr_code",
  "other_text",
];
const CHECKS = [
  ["required_field", "Must be present"],
  ["pattern", "Must contain wording (pattern)"],
  ["claim_keywords", "Claim keywords → review"],
  ["date_not_expired", "Date not passed"],
];
type Form = {
  code: string;
  title: string;
  category: string;
  check_type: string;
  field: string;
  pattern: string;
  keywords: string;
  severity: string;
  requirement: string;
  reference: string;
  status: string;
  notes: string;
  change_note: string;
};
const blank: Form = {
  code: "",
  title: "",
  category: "all",
  check_type: "required_field",
  field: "allergens",
  pattern: "",
  keywords: "",
  severity: "warning",
  requirement: "",
  reference: "FSS (Labelling & Display) Regulations, 2020",
  status: "draft",
  notes: "",
  change_note: "",
};

export default function ComplianceRules() {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [data, setData] = useState<Page<Rule> | null>(null);
  const [stats, setStats] = useState<S["RulesStatsOut"] | null>(null);
  const [view, setView] = useState<Rule | null>(null);
  const [form, setForm] = useState<Form | null>(null);
  const [editId, setEditId] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api<Page<Rule>>("/api/v1/admin/rules", { query: { q, category, status, page_size: 100 } })
      .then(setData)
      .catch((e) => setErr(errorMessage(e)));
    api<S["RulesStatsOut"]>("/api/v1/admin/rules/stats")
      .then(setStats)
      .catch(() => undefined);
  }, [q, category, status]);
  useEffect(() => {
    const t = window.setTimeout(load, 250);
    return () => window.clearTimeout(t);
  }, [load]);

  function openEdit(r: Rule | null) {
    setErrors({});
    setErr(null);
    setEditId(r?.id ?? null);
    setForm(
      r
        ? {
            code: r.code,
            title: r.title,
            category: r.category,
            check_type: r.check_type,
            field: r.field,
            pattern: r.pattern ?? "",
            keywords: r.keywords.join(", "),
            severity: r.severity,
            requirement: r.requirement,
            reference: r.reference,
            status: r.status,
            notes: r.notes,
            change_note: "",
          }
        : { ...blank },
    );
  }
  async function save() {
    if (!form) return;
    setBusy(true);
    setErrors({});
    setErr(null);
    const body: Record<string, unknown> = {
      ...form,
      pattern: form.pattern || null,
      keywords: form.keywords
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    };
    try {
      if (editId) {
        delete body.code;
        await api(`/api/v1/admin/rules/${editId}`, { method: "PATCH", body });
      } else {
        delete body.change_note;
        await api("/api/v1/admin/rules", { method: "POST", body });
      }
      setForm(null);
      load();
    } catch (e) {
      if (e instanceof ApiError && e.fields) setErrors(e.fields);
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  async function archive(r: Rule) {
    try {
      await api(`/api/v1/admin/rules/${r.id}/archive`, { method: "POST" });
      setView(null);
      load();
    } catch (e) {
      setErr(errorMessage(e));
    }
  }
  const set = (k: keyof Form) => (e: { target: { value: string } }) => form && setForm({ ...form, [k]: e.target.value });

  return (
    <>
      <PageHeader
        title="Compliance Rules"
        subtitle="Demonstration labelling rules applied during inspections, by food category."
        actions={
          <Button iconRight="plus" onClick={() => openEdit(null)}>
            Add Rule
          </Button>
        }
      />
      <Notice>
        These rules are maintained by hand and derived from published FSSAI regulations for demonstration purposes. They are not an
        authoritative restatement of the law, and the system does not issue legal compliance verdicts. Rule wording and references must be
        verified by the owner.
      </Notice>
      {err && !form && <ErrorBox error={err} />}
      <div className="grid gap-4 cs-grid" style={{ gridTemplateColumns: "repeat(4, minmax(0, 1fr))" }}>
        <Metric icon="rules" value={stats?.active ?? "—"} labelText="Active rules" />
        <Metric icon="file" value={stats?.draft ?? "—"} labelText="Draft rules" />
        <Metric icon="box" value={stats?.categories ?? "—"} labelText="Categories covered" />
        <Metric icon="clock" value={stats?.last_update ? fmtDate(stats.last_update).slice(0, 6) : "—"} labelText="Last rule update" />
      </div>
      <Panel>
        <div className="flex flex-wrap items-end gap-3 mb-4">
          <div className="flex-[1_1_220px] max-w-[300px]">
            <SearchBox value={q} onChange={setQ} placeholder="Rule name, ID or reference" />
          </div>
          <SelectField label="Category" value={category} onChange={(e) => setCategory(e.target.value)} className="w-[190px]">
            <option value="">All categories</option>
            {Object.entries(CATEGORY_LABELS).map(([k, l]) => (
              <option key={k} value={k}>
                {l}
              </option>
            ))}
          </SelectField>
          <SelectField label="Status" value={status} onChange={(e) => setStatus(e.target.value)} className="w-[150px]">
            <option value="">Active & draft</option>
            <option value="active">Active</option>
            <option value="draft">Draft</option>
            <option value="archived">Archived</option>
          </SelectField>
        </div>
        {!data ? (
          <LoadingBlock rows={6} />
        ) : data.items.length === 0 ? (
          <Empty icon="rules" title="No rules match" />
        ) : (
          <table className="cs-table">
            <thead>
              <tr>
                <th>Rule ID</th>
                <th>Rule Name</th>
                <th>Category</th>
                <th>Regulatory Reference</th>
                <th>Status</th>
                <th>Last Updated</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((r) => (
                <tr key={r.id}>
                  <td>
                    <span style={{ fontWeight: 700, color: "#55584E" }}>{r.code}</span>
                  </td>
                  <td>
                    <strong>{r.title}</strong>
                    <div style={{ fontSize: 12, color: "#686B60" }}>
                      v{r.version} · {CHECKS.find(([k]) => k === r.check_type)?.[1]}
                    </div>
                  </td>
                  <td>
                    <span className="cs-cell-label">Category</span>
                    {CATEGORY_LABELS[r.category]}
                  </td>
                  <td>
                    <span className="cs-cell-label">Reference</span>
                    <span style={{ fontSize: 13 }}>{r.reference || "—"}</span>
                  </td>
                  <td>
                    <Chip status={r.status} />
                  </td>
                  <td>
                    <span className="cs-cell-label">Last updated</span>
                    {fmtDate(r.updated_at)}
                  </td>
                  <td>
                    <div className="flex gap-2">
                      <IconButton icon="eye" label={`View ${r.code}`} onClick={() => setView(r)} />
                      {r.status !== "archived" && <IconButton icon="edit" label={`Edit ${r.code}`} onClick={() => openEdit(r)} />}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Panel>
      <Panel title="What a rule contains">
        <div className="grid gap-3 cs-grid" style={{ gridTemplateColumns: "repeat(4, minmax(0, 1fr))" }}>
          {[
            ["Requirement", "What the label must carry, in plain words."],
            ["Applies to", "One food category, or all categories."],
            ["Check logic", "Which extracted field is checked, and how: present, wording, claim keywords or date."],
            ["Regulatory reference", "The published source it is based on, kept with a version history."],
          ].map(([t, d]) => (
            <div key={t} className="rounded-[10px] border border-line p-3.5" style={{ background: "#FBF8F0" }}>
              <strong className="block" style={{ fontSize: 14 }}>
                {t}
              </strong>
              <span style={{ fontSize: 13, color: "#55584E" }}>{d}</span>
            </div>
          ))}
        </div>
      </Panel>

      <Modal
        open={!!view}
        title={view ? `${view.code} · ${view.title}` : ""}
        onClose={() => setView(null)}
        wide
        footer={
          view && view.status !== "archived" ? (
            <>
              <Button variant="danger" onClick={() => void archive(view)}>
                Archive rule
              </Button>
              <Button
                onClick={() => {
                  openEdit(view);
                  setView(null);
                }}
              >
                Edit
              </Button>
            </>
          ) : undefined
        }
      >
        {view && (
          <div className="flex flex-col gap-3" style={{ fontSize: 14 }}>
            <dl className="grid grid-cols-2 gap-3 m-0 max-[760px]:grid-cols-1">
              {[
                ["Requirement", view.requirement],
                ["Category", CATEGORY_LABELS[view.category]],
                ["Field checked", view.field],
                ["Check", CHECKS.find(([k]) => k === view.check_type)?.[1]],
                ["Pattern", view.pattern || "—"],
                ["Keywords", view.keywords.join(", ") || "—"],
                ["Severity", label(view.severity)],
                ["Reference", view.reference || "—"],
                ["Status", label(view.status)],
                ["Version", `v${view.version}`],
                ["Notes", view.notes || "—"],
              ].map(([k, v]) => (
                <div key={k}>
                  <dt className="cs-label">{k}</dt>
                  <dd className="m-0" style={{ overflowWrap: "anywhere" }}>
                    {v}
                  </dd>
                </div>
              ))}
            </dl>
            <div>
              <div className="cs-label mb-1">Version history</div>
              <ul className="m-0 pl-4">
                {[...view.history].reverse().map((h, i) => (
                  <li key={i}>
                    v{String(h.version)} · {String(h.note)} · {String(h.by)} · {fmtDate(String(h.at), true)}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </Modal>
      <Modal
        open={!!form}
        title={editId ? "Edit rule" : "Add rule"}
        onClose={() => setForm(null)}
        wide
        footer={
          <>
            <Button variant="secondary" onClick={() => setForm(null)}>
              Cancel
            </Button>
            <Button working={busy} onClick={() => void save()}>
              {editId ? "Save new version" : "Create rule"}
            </Button>
          </>
        }
      >
        {form && (
          <div className="flex flex-col gap-3">
            {err && <ErrorBox error={err} />}
            <div className="grid grid-cols-2 gap-3 max-[760px]:grid-cols-1">
              <TextField
                label="Rule ID"
                value={form.code}
                onChange={set("code")}
                disabled={!!editId}
                error={errors.code}
                placeholder="DR-FS-12"
                maxLength={20}
              />
              <TextField label="Rule name" value={form.title} onChange={set("title")} error={errors.title} maxLength={200} />
              <SelectField label="Category" value={form.category} onChange={set("category")}>
                {Object.entries(CATEGORY_LABELS).map(([k, l]) => (
                  <option key={k} value={k}>
                    {l}
                  </option>
                ))}
              </SelectField>
              <SelectField label="Status" value={form.status} onChange={set("status")}>
                <option value="draft">Draft</option>
                <option value="active">Active</option>
              </SelectField>
              <SelectField label="Check logic" value={form.check_type} onChange={set("check_type")}>
                {CHECKS.map(([k, l]) => (
                  <option key={k} value={k}>
                    {l}
                  </option>
                ))}
              </SelectField>
              <SelectField label="Field checked" value={form.field} onChange={set("field")}>
                {FIELD_OPTIONS.map((f) => (
                  <option key={f} value={f}>
                    {f.replace(/_/g, " ")}
                  </option>
                ))}
              </SelectField>
              {form.check_type === "pattern" && (
                <TextField
                  label="Pattern (regular expression, case-insensitive)"
                  value={form.pattern}
                  onChange={set("pattern")}
                  error={errors.pattern}
                  maxLength={200}
                />
              )}
              {form.check_type === "claim_keywords" && (
                <TextField label="Keywords (comma separated)" value={form.keywords} onChange={set("keywords")} error={errors.keywords} />
              )}
              <SelectField label="Severity" value={form.severity} onChange={set("severity")}>
                <option value="info">Info</option>
                <option value="warning">Warning</option>
                <option value="high">High</option>
              </SelectField>
              <TextField label="Regulatory reference" value={form.reference} onChange={set("reference")} maxLength={200} />
            </div>
            <TextArea
              label="Requirement"
              value={form.requirement}
              onChange={set("requirement")}
              error={errors.requirement}
              maxLength={2000}
            />
            <TextArea label="Notes" value={form.notes} onChange={set("notes")} maxLength={2000} />
            {editId && (
              <TextField
                label="Change note (kept in version history)"
                value={form.change_note}
                onChange={set("change_note")}
                maxLength={200}
              />
            )}
            {errors.request && <span className="cs-field-error">{errors.request}</span>}
          </div>
        )}
      </Modal>
    </>
  );
}
