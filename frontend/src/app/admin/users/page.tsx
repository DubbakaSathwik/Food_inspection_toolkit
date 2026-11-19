"use client";

import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icon";
import { PageHeader } from "@/components/shell";
import {
  Button,
  Chip,
  Empty,
  ErrorBox,
  fmtDate,
  IconButton,
  initials,
  label,
  LoadingBlock,
  Metric,
  Modal,
  Notice,
  Panel,
  SearchBox,
  SelectField,
  TextField,
} from "@/components/ui";
import { api, errorMessage, type AdminUser, type Page, type S } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Detail = S["UserDetailOut"];
type Invite = S["InviteOut"];

export default function UserManagement() {
  const { me } = useAuth();
  const isSuper = me?.role === "super_admin";
  const [query, setQuery] = useState("");
  const [roleF, setRoleF] = useState("");
  const [statF, setStatF] = useState(() =>
    typeof window === "undefined" ? "" : (new URLSearchParams(window.location.search).get("status") ?? ""),
  );
  const [data, setData] = useState<Page<AdminUser> | null>(null);
  const [pending, setPending] = useState<AdminUser[]>([]);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [invites, setInvites] = useState<Invite[]>([]);
  const [roles, setRoles] = useState<Record<string, string>>({});
  const [view, setView] = useState<Detail | null>(null);
  const [edit, setEdit] = useState<AdminUser | null>(null);
  const [editRole, setEditRole] = useState("inspector");
  const [addOpen, setAddOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newRole, setNewRole] = useState("inspector");
  const [notice, setNotice] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(() => {
    api<Page<AdminUser>>("/api/v1/admin/users", { query: { q: query, role: roleF, status: statF, page_size: 100 } })
      .then(setData)
      .catch((e) => setErr(errorMessage(e)));
    api<Page<AdminUser>>("/api/v1/admin/users", { query: { status: "pending", page_size: 50 } })
      .then((p) => setPending(p.items))
      .catch(() => undefined);
    Promise.all(
      [
        ["inspectors", { role: "inspector" }],
        ["active", { status: "active" }],
        ["pending", { status: "pending" }],
        ["admins", { role: "admin" }],
        ["supers", { role: "super_admin" }],
      ].map(([k, qy]) =>
        api<Page<AdminUser>>("/api/v1/admin/users", { query: { ...(qy as object), page_size: 1 } }).then(
          (p) => [k as string, p.total] as const,
        ),
      ),
    )
      .then((r) => setCounts(Object.fromEntries(r)))
      .catch(() => undefined);
    api<Invite[]>("/api/v1/admin/users/invites")
      .then(setInvites)
      .catch(() => undefined);
  }, [query, roleF, statF]);
  useEffect(() => {
    const t = window.setTimeout(load, 250);
    return () => window.clearTimeout(t);
  }, [load]);

  async function run(key: string, fn: () => Promise<unknown>, msg: string) {
    setBusy(key);
    setErr(null);
    try {
      await fn();
      setNotice(msg);
      load();
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(null);
    }
  }
  const approve = (u: AdminUser) =>
    run(
      `a-${u.uid}`,
      () => api(`/api/v1/admin/users/${u.uid}/approve`, { method: "POST", body: { role: roles[u.uid] ?? "inspector" } }),
      `${u.email} approved as ${label(roles[u.uid] ?? "inspector")}. They get access on their next page load.`,
    );
  const decline = (u: AdminUser) =>
    run(`d-${u.uid}`, () => api(`/api/v1/admin/users/${u.uid}/decline`, { method: "POST" }), `${u.email} declined.`);
  const toggle = (u: AdminUser) =>
    run(
      `t-${u.uid}`,
      () => api(`/api/v1/admin/users/${u.uid}`, { method: "PATCH", body: { status: u.status === "active" ? "disabled" : "active" } }),
      `${u.email} ${u.status === "active" ? "disabled — signed out of all sessions" : "re-enabled"}.`,
    );
  const protectedRow = (u: AdminUser) => u.uid === me?.uid || ((u.role === "admin" || u.role === "super_admin") && !isSuper);

  return (
    <>
      <PageHeader title="User Management" subtitle="Inspectors, administrators and account approvals." />
      {notice && (
        <Notice tone="ok" icon="check">
          {notice}
        </Notice>
      )}
      {err && <ErrorBox error={err} />}
      <div className="grid gap-4 cs-grid" style={{ gridTemplateColumns: "repeat(4, minmax(0, 1fr))" }}>
        <Metric icon="users" value={counts.inspectors ?? "—"} labelText="Registered inspectors" />
        <Metric icon="check" value={counts.active ?? "—"} labelText="Active accounts" />
        <Metric icon="clock" value={counts.pending ?? "—"} labelText="Awaiting approval" highlight />
        <Metric icon="shield" value={(counts.admins ?? 0) + (counts.supers ?? 0) || "—"} labelText="Administrators" />
      </div>
      <Panel
        title="Accounts awaiting approval"
        action={
          <Chip tone="warn" dot={false}>
            {pending.length} account{pending.length === 1 ? "" : "s"} waiting
          </Chip>
        }
      >
        <p className="mt-0" style={{ fontSize: 13.5, color: "#55584E" }}>
          Anyone can sign in with Google, but a new account stays on the waiting screen until an administrator activates it. Roles are
          assigned here, never chosen by the user.
        </p>
        {pending.length === 0 ? (
          <span style={{ fontSize: 13.5, color: "#686B60" }}>No accounts waiting.</span>
        ) : (
          <div className="flex flex-col gap-2.5">
            {pending.map((u) => (
              <div
                key={u.uid}
                className="flex flex-wrap items-center gap-3 rounded-[10px] border border-line px-4 py-3"
                style={{ background: "#FBF8F0" }}
              >
                <span
                  className="grid place-items-center rounded-full shrink-0"
                  style={{ width: 36, height: 36, background: "#E3EACF", fontWeight: 700, fontSize: 13 }}
                >
                  {initials(u.name)}
                </span>
                <span className="flex-1 min-w-[180px]">
                  <strong className="block">{u.name}</strong>
                  <span style={{ fontSize: 13, color: "#55584E", overflowWrap: "anywhere" }}>
                    {u.email} · Signed in {fmtDate(u.created_at)}
                  </span>
                </span>
                <div className="flex flex-wrap items-center gap-2 cs-acts">
                  <label className="sr-only" htmlFor={`r-${u.uid}`}>
                    Role for {u.email}
                  </label>
                  <select
                    id={`r-${u.uid}`}
                    className="cs-select"
                    style={{ width: "auto" }}
                    value={roles[u.uid] ?? "inspector"}
                    onChange={(e) => setRoles({ ...roles, [u.uid]: e.target.value })}
                  >
                    <option value="inspector">Inspector</option>
                    {isSuper && <option value="admin">Admin</option>}
                    {isSuper && <option value="super_admin">Super Admin</option>}
                  </select>
                  <Button small icon="tick" working={busy === `a-${u.uid}`} onClick={() => void approve(u)}>
                    Approve
                  </Button>
                  <Button small variant="secondary" working={busy === `d-${u.uid}`} onClick={() => void decline(u)}>
                    Decline
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>
      <Panel>
        <div className="flex flex-wrap items-end gap-3 mb-4">
          <div className="flex-[1_1_220px] max-w-[300px]">
            <SearchBox value={query} onChange={setQuery} placeholder="Name or email" />
          </div>
          <SelectField label="Role" value={roleF} onChange={(e) => setRoleF(e.target.value)} className="w-[150px]">
            <option value="">All roles</option>
            <option value="inspector">Inspector</option>
            <option value="admin">Admin</option>
            <option value="super_admin">Super Admin</option>
          </SelectField>
          <SelectField label="Status" value={statF} onChange={(e) => setStatF(e.target.value)} className="w-[140px]">
            <option value="">All</option>
            <option value="active">Active</option>
            <option value="pending">Pending</option>
            <option value="disabled">Inactive</option>
            <option value="declined">Declined</option>
          </SelectField>
          <div className="ml-auto max-[760px]:w-full">
            <Button icon="plus" className="max-[760px]:w-full" onClick={() => setAddOpen(true)}>
              Add user
            </Button>
          </div>
        </div>
        {!data ? (
          <LoadingBlock rows={6} />
        ) : data.items.length === 0 ? (
          <Empty icon="users" title="No users match" />
        ) : (
          <table className="cs-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Account Status</th>
                <th>Registered</th>
                <th>Inspections</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((u) => (
                <tr key={u.uid}>
                  <td>
                    <strong>{u.name}</strong>
                    {u.uid === me?.uid && <span style={{ fontSize: 12, color: "#686B60" }}> (you)</span>}
                  </td>
                  <td>
                    <span className="cs-cell-label">Email</span>
                    <span style={{ overflowWrap: "anywhere" }}>{u.email}</span>
                  </td>
                  <td>
                    <span className="cs-cell-label">Role</span>
                    {u.role ? <Chip status={u.role} dot={false} tone="neu" /> : "—"}
                  </td>
                  <td>
                    <span className="cs-cell-label">Status</span>
                    <Chip status={u.status} />
                  </td>
                  <td>
                    <span className="cs-cell-label">Registered</span>
                    {fmtDate(u.created_at)}
                  </td>
                  <td>
                    <span className="cs-cell-label">Inspections</span>
                    {u.role === "inspector" ? u.inspections : "-"}
                  </td>
                  <td>
                    <div className="flex items-center gap-2">
                      <IconButton
                        icon="eye"
                        label={`View ${u.email}`}
                        onClick={() =>
                          void api<Detail>(`/api/v1/admin/users/${u.uid}`)
                            .then(setView)
                            .catch((e) => setErr(errorMessage(e)))
                        }
                      />
                      {protectedRow(u) ? (
                        <span className="inline-flex items-center gap-1" style={{ fontSize: 12.5, color: "#686B60" }}>
                          <Icon name="lock" size={14} />
                          Protected
                        </span>
                      ) : (
                        <>
                          {u.status === "active" || u.status === "disabled" ? (
                            <IconButton
                              icon="edit"
                              label={`Edit role of ${u.email}`}
                              onClick={() => {
                                setEdit(u);
                                setEditRole(u.role ?? "inspector");
                              }}
                            />
                          ) : null}
                          {(u.status === "active" || u.status === "disabled") && (
                            <IconButton
                              icon={u.status === "active" ? "pause" : "play"}
                              label={u.status === "active" ? `Disable ${u.email}` : `Enable ${u.email}`}
                              onClick={() => void toggle(u)}
                            />
                          )}
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <p className="mb-0" style={{ fontSize: 12.5, color: "#686B60" }}>
          Creating administrators, changing administrator roles and managing administrator accounts are Super Admin actions. Ordinary
          administrators do not see those controls.
        </p>
      </Panel>
      {invites.length > 0 && (
        <Panel title="Pre-authorised sign-ins">
          <table className="cs-table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Name</th>
                <th>Role on first sign-in</th>
                <th>Added</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {invites.map((i) => (
                <tr key={i.email}>
                  <td>{i.email}</td>
                  <td>{i.name || "—"}</td>
                  <td>
                    <Chip status={i.role} dot={false} tone="neu" />
                  </td>
                  <td>
                    {fmtDate(i.created_at)} by {i.created_by_name}
                  </td>
                  <td>
                    <IconButton
                      icon="trash"
                      label={`Revoke ${i.email}`}
                      onClick={() =>
                        void run(
                          `i-${i.email}`,
                          () => api(`/api/v1/admin/users/invites/${encodeURIComponent(i.email)}`, { method: "DELETE" }),
                          `Invitation for ${i.email} revoked.`,
                        )
                      }
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      )}

      <Modal open={!!view} title={view?.name ?? "User"} onClose={() => setView(null)}>
        {view && (
          <div className="flex flex-col gap-3" style={{ fontSize: 14 }}>
            <div>{view.email}</div>
            <div className="flex gap-2">
              <Chip status={view.role ?? "pending"} />
              <Chip status={view.status} />
            </div>
            <dl className="grid grid-cols-2 gap-3 m-0">
              {[
                ["Designation", view.designation || "—"],
                ["Office", view.office || "—"],
                ["Registered", fmtDate(view.created_at)],
                ["Approved", fmtDate(view.approved_at)],
                ["Last active", fmtDate(view.last_active_at, true)],
                ["Inspections", `${view.inspections} (${view.completed_inspections} completed)`],
                ["Proposals", String(view.proposals)],
              ].map(([k, v]) => (
                <div key={k}>
                  <dt className="cs-label">{k}</dt>
                  <dd className="m-0 font-bold">{v}</dd>
                </div>
              ))}
            </dl>
            {view.recent.length > 0 && (
              <div>
                <div className="cs-label mb-1">Recent inspections (titles only — report contents stay private)</div>
                <ul className="m-0 pl-4">
                  {view.recent.map((r) => (
                    <li key={r.id}>
                      {r.id} · {r.product} · {label(r.status)} · {r.date}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </Modal>
      <Modal
        open={!!edit}
        title={`Change role — ${edit?.email ?? ""}`}
        onClose={() => setEdit(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setEdit(null)}>
              Cancel
            </Button>
            <Button
              working={busy === "edit"}
              onClick={() =>
                edit &&
                void run(
                  "edit",
                  () => api(`/api/v1/admin/users/${edit.uid}`, { method: "PATCH", body: { role: editRole } }),
                  `${edit.email} is now ${label(editRole)}.`,
                ).then(() => setEdit(null))
              }
            >
              Save
            </Button>
          </>
        }
      >
        <SelectField label="Role" value={editRole} onChange={(e) => setEditRole(e.target.value)}>
          <option value="inspector">Inspector</option>
          {isSuper && <option value="admin">Admin</option>}
          {isSuper && <option value="super_admin">Super Admin</option>}
        </SelectField>
        <p style={{ fontSize: 13, color: "#55584E" }}>
          The change applies on the user&apos;s next request; their old permissions stop working immediately.
        </p>
      </Modal>
      <Modal
        open={addOpen}
        title="Add user"
        onClose={() => setAddOpen(false)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setAddOpen(false)}>
              Cancel
            </Button>
            <Button
              working={busy === "add"}
              disabled={!newEmail.includes("@")}
              onClick={() =>
                void run(
                  "add",
                  () =>
                    api("/api/v1/admin/users/invites", {
                      method: "POST",
                      body: { email: newEmail.trim(), name: newName.trim(), role: newRole },
                    }),
                  `${newEmail} is pre-authorised as ${label(newRole)} — they get access when they first sign in with Google.`,
                ).then(() => {
                  setAddOpen(false);
                  setNewEmail("");
                  setNewName("");
                })
              }
            >
              Add user
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-3">
          <Notice>The person still signs in with their own Google account. Adding them here skips the waiting screen.</Notice>
          <TextField label="Name" value={newName} onChange={(e) => setNewName(e.target.value)} maxLength={200} />
          <TextField
            label="Google account email"
            type="email"
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
            maxLength={320}
          />
          <SelectField label="Role" value={newRole} onChange={(e) => setNewRole(e.target.value)}>
            <option value="inspector">Inspector</option>
            {isSuper && <option value="admin">Admin</option>}
            {isSuper && <option value="super_admin">Super Admin</option>}
          </SelectField>
        </div>
      </Modal>
    </>
  );
}
