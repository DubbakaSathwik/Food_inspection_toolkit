"use client";

import { useEffect, useState } from "react";
import { Button, Chip, ErrorBox, fmtDate, initials, label, Metric, Panel, TextField } from "@/components/ui";
import { api, errorMessage, type Me, type S } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export function ProfileView({ showActivity = true }: { showActivity?: boolean }) {
  const { me, signOut, reload } = useAuth();
  const [dash, setDash] = useState<S["DashboardOut"] | null>(null);
  const [form, setForm] = useState(() => ({
    name: me?.name ?? "",
    designation: me?.designation ?? "",
    office: me?.office ?? "",
    phone: me?.phone ?? "",
  }));
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [fieldErr, setFieldErr] = useState<Record<string, string>>({});

  useEffect(() => {
    if (showActivity)
      api<S["DashboardOut"]>("/api/v1/inspector/dashboard")
        .then(setDash)
        .catch(() => undefined);
  }, [showActivity]);

  async function save() {
    setBusy(true);
    setErr(null);
    setFieldErr({});
    try {
      await api<Me>("/api/v1/me", { method: "PATCH", body: form });
      await reload();
      setEditing(false);
    } catch (e) {
      const f = (e as { fields?: Record<string, string> }).fields;
      if (f) setFieldErr(f);
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  if (!me) return null;
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value });
  return (
    <div className="grid grid-cols-[300px_minmax(0,1fr)] gap-5 items-start max-[960px]:grid-cols-1">
      <section className="cs-panel flex flex-col items-center gap-3 text-center" aria-label="Account">
        <span
          className="grid place-items-center rounded-full"
          style={{ width: 80, height: 80, background: "#56703A", color: "#fff", fontSize: 26, fontWeight: 700 }}
        >
          {initials(me.name)}
        </span>
        <strong style={{ fontSize: 19 }}>{me.name}</strong>
        <span style={{ fontSize: 13.5, color: "#55584E", overflowWrap: "anywhere" }}>{me.email}</span>
        <span className="flex gap-2">
          <Chip status={me.role ?? "pending"} />
          <Chip status={me.status} />
        </span>
        <p className="m-0" style={{ fontSize: 13, color: "#55584E", lineHeight: 1.55 }}>
          Signed in with Google. Your name and email come from that account and are shown on the reports you generate.
        </p>
        <div className="w-full pt-3 border-t border-line">
          <Button variant="secondary" icon="logout" className="w-full" onClick={() => void signOut()}>
            Sign out
          </Button>
        </div>
      </section>
      <div className="flex flex-col gap-5 min-w-0">
        <Panel
          title="Account details"
          action={
            !editing && (
              <Button
                small
                variant="secondary"
                icon="edit"
                onClick={() => {
                  setForm({ name: me.name, designation: me.designation ?? "", office: me.office ?? "", phone: me.phone ?? "" });
                  setEditing(true);
                }}
              >
                Edit
              </Button>
            )
          }
        >
          {err && (
            <div className="mb-3">
              <ErrorBox error={err} />
            </div>
          )}
          {editing ? (
            <div className="grid grid-cols-2 gap-3 max-[760px]:grid-cols-1">
              <TextField label="Display name" value={form.name} onChange={set("name")} maxLength={200} error={fieldErr.name} />
              <TextField
                label="Designation"
                value={form.designation}
                onChange={set("designation")}
                maxLength={200}
                placeholder="Food Safety Officer"
              />
              <TextField
                label="Office / jurisdiction"
                value={form.office}
                onChange={set("office")}
                maxLength={200}
                placeholder="District / zone"
              />
              <TextField label="Phone" value={form.phone} onChange={set("phone")} maxLength={40} error={fieldErr.phone} inputMode="tel" />
              <div className="col-span-2 max-[760px]:col-span-1 flex gap-2.5 cs-acts">
                <Button working={busy} onClick={() => void save()}>
                  Save changes
                </Button>
                <Button variant="secondary" onClick={() => setEditing(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <dl className="grid grid-cols-2 gap-x-6 gap-y-3 m-0 max-[760px]:grid-cols-1" style={{ fontSize: 14 }}>
              {[
                ["Role", label(me.role)],
                ["Account status", label(me.status)],
                ["Designation", me.designation || "—"],
                ["Jurisdiction", me.office || "—"],
                ["Phone", me.phone || "—"],
                ["Member since", fmtDate(me.created_at)],
                ["Interface language", "English"],
              ].map(([k, v]) => (
                <div key={k}>
                  <dt className="cs-label">{k}</dt>
                  <dd className="m-0 font-bold">{v}</dd>
                </div>
              ))}
            </dl>
          )}
        </Panel>
        {showActivity && (
          <Panel title="Your activity">
            <div className="grid gap-3 cs-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))" }}>
              <Metric icon="doc" value={dash?.total ?? "—"} labelText="Inspections" />
              <Metric icon="check" value={dash?.by_classification.verified ?? "—"} labelText="Verified" />
              <Metric icon="alert" value={dash?.by_classification.suspicious ?? "—"} labelText="Suspicious" />
              <Metric icon="proposal" value={dash?.proposals ?? "—"} labelText="Proposals" />
            </div>
          </Panel>
        )}
        <Panel title="Data and privacy">
          <ul className="m-0 pl-4 list-disc flex flex-col gap-2" style={{ fontSize: 14, color: "#3a3d35" }}>
            <li>Only you can open your inspection records and reports.</li>
            <li>Administrators can see your account status and activity totals, not your report contents.</li>
            <li>Original photographs are deleted after the report is generated; compressed copies stay embedded in the PDF.</li>
          </ul>
        </Panel>
      </div>
    </div>
  );
}
