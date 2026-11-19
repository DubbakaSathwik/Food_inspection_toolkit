"use client";

import Link from "next/link";
import {
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type MouseEvent,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
  useEffect,
  useId,
  useRef,
} from "react";
import { Icon, type IconName } from "./icon";

/* ---------------------------------------------------------------- Logo */
export function Logo({ size = 32, text = 19 }: { size?: number; text?: number }) {
  return (
    <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <svg width={size} height={size} viewBox="0 0 40 40" fill="none" aria-hidden style={{ flexShrink: 0 }}>
        <path
          d="M4 13V6a2 2 0 0 1 2-2h7M27 4h7a2 2 0 0 1 2 2v7M36 27v7a2 2 0 0 1-2 2h-7M13 36H6a2 2 0 0 1-2-2v-7"
          stroke="#56703A"
          strokeWidth="2.6"
          strokeLinecap="round"
        />
        <path d="M13 26c0-8 5-13 14-13 0 9-5 14-13 14" stroke="#56703A" strokeWidth="2.2" strokeLinejoin="round" fill="#C5D89D" />
        <path d="M13 27l8-8" stroke="#56703A" strokeWidth="2" strokeLinecap="round" />
      </svg>
      <span style={{ fontSize: text, fontWeight: 800, letterSpacing: -0.2, color: "#20231D" }}>CRATE-SCAN</span>
    </span>
  );
}

/* ---------------------------------------------------------------- Buttons */
function ripple(e: MouseEvent<HTMLElement>) {
  const el = e.currentTarget;
  const r = el.getBoundingClientRect();
  const s = document.createElement("span");
  s.className = "cs-rip";
  s.style.left = `${e.clientX - r.left}px`;
  s.style.top = `${e.clientY - r.top}px`;
  el.appendChild(s);
  setTimeout(() => s.remove(), 650);
}

type Variant = "primary" | "secondary" | "danger";
const vClass = (v: Variant) => (v === "primary" ? "cs-btn" : v === "danger" ? "cs-btn2 cs-btn-danger" : "cs-btn2");

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  small?: boolean;
  icon?: IconName;
  iconRight?: IconName;
  working?: boolean;
};

export function Button({
  variant = "primary",
  small,
  icon,
  iconRight,
  working,
  className = "",
  children,
  onClick,
  disabled,
  ...rest
}: BtnProps) {
  return (
    <button
      type="button"
      {...rest}
      disabled={disabled || working}
      aria-busy={working || undefined}
      className={`${vClass(variant)} ${small ? "cs-btn-sm" : ""} ${working ? "cs-working" : ""} ${className}`}
      onClick={(e) => {
        ripple(e);
        onClick?.(e);
      }}
    >
      {icon && <Icon name={icon} size={17} />}
      {children}
      {iconRight && <Icon name={iconRight} size={17} />}
    </button>
  );
}

export function ButtonLink({
  href,
  variant = "primary",
  small,
  icon,
  iconRight,
  children,
  className = "",
}: {
  href: string;
  variant?: Variant;
  small?: boolean;
  icon?: IconName;
  iconRight?: IconName;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Link href={href} onClick={ripple} className={`${vClass(variant)} ${small ? "cs-btn-sm" : ""} ${className}`}>
      {icon && <Icon name={icon} size={17} />}
      {children}
      {iconRight && <Icon name={iconRight} size={17} />}
    </Link>
  );
}

export function IconButton({
  icon,
  label,
  onClick,
  disabled,
  className = "",
}: {
  icon: IconName;
  label: string;
  onClick?: () => void;
  disabled?: boolean;
  className?: string;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      className={`cs-ib ${className}`}
      onClick={(e) => {
        ripple(e);
        onClick?.();
      }}
    >
      <Icon name={icon} size={17} />
    </button>
  );
}

/* ---------------------------------------------------------------- Chips */
export type Tone = "ok" | "warn" | "bad" | "neu" | "info" | "tint";
const TONES: Record<string, Tone> = {
  verified: "ok",
  approved: "ok",
  active: "ok",
  completed: "ok",
  exact: "ok",
  match: "ok",
  found: "ok",
  pass: "ok",
  auto: "ok",
  confirmed: "ok",
  not_verified: "neu",
  draft: "neu",
  archived: "neu",
  inactive: "neu",
  not_applicable: "neu",
  missing: "neu",
  info: "info",
  suspicious: "warn",
  pending: "warn",
  awaiting_approval: "warn",
  partial: "warn",
  warning: "warn",
  review: "warn",
  incomplete: "warn",
  extracted: "warn",
  analysed: "warn",
  needs_review: "warn",
  edited: "info",
  info_requested: "info",
  in_review: "info",
  rejected: "bad",
  disabled: "bad",
  declined: "bad",
  mismatch: "bad",
  high: "bad",
  fail: "bad",
  expired: "bad",
  suspended: "bad",
  invalid_format: "bad",
  differs: "warn",
  no_record: "neu",
  not_found: "neu",
  insufficient: "neu",
  inspector: "tint",
  admin: "info",
  super_admin: "info",
};
export const LABELS: Record<string, string> = {
  verified: "Verified",
  not_verified: "Not verified",
  suspicious: "Suspicious",
  pending: "Pending",
  approved: "Approved",
  rejected: "Rejected",
  info_requested: "Info requested",
  active: "Active",
  draft: "Draft",
  archived: "Archived",
  disabled: "Inactive",
  declined: "Declined",
  inspector: "Inspector",
  admin: "Admin",
  super_admin: "Super Admin",
  completed: "Completed",
  incomplete: "Incomplete",
  extracted: "Fields to check",
  analysed: "Awaiting your review",
  exact: "Exact match",
  partial: "Partial match",
  mismatch: "Mismatch",
  no_record: "No record",
  insufficient: "Insufficient info",
  in_review: "In review",
  awaiting_approval: "Awaiting approval",
};
export const label = (s: string | null | undefined) =>
  s ? (LABELS[s] ?? s.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase())) : "—";

export function Chip({ status, tone, children, dot = true }: { status?: string | null; tone?: Tone; children?: ReactNode; dot?: boolean }) {
  const t = tone ?? TONES[status ?? ""] ?? "neu";
  return (
    <span className={`cs-chip tone-${t}`}>
      {dot && <span className="dot" aria-hidden />}
      {children ?? label(status)}
    </span>
  );
}

export function Pill({ children, tone = "tint" }: { children: ReactNode; tone?: Tone }) {
  return (
    <span className={`cs-chip tone-${tone}`} style={{ borderRadius: 999, fontWeight: 700 }}>
      {children}
    </span>
  );
}

/* ---------------------------------------------------------------- Layout pieces */
export function Panel({
  children,
  className = "",
  title,
  action,
  id,
}: {
  children: ReactNode;
  className?: string;
  title?: ReactNode;
  action?: ReactNode;
  id?: string;
}) {
  return (
    <section className={`cs-panel ${className}`} id={id} aria-label={typeof title === "string" ? title : undefined}>
      {(title || action) && (
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          {title && <h2 className="cs-h2">{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function Metric({
  icon,
  value,
  labelText,
  highlight,
}: {
  icon: IconName;
  value: ReactNode;
  labelText: string;
  highlight?: boolean;
}) {
  return (
    <div
      className="flex flex-col gap-3.5 rounded-[12px] border border-line p-[22px] max-[760px]:p-4"
      style={{ background: highlight ? "#EEF2E1" : "#fff" }}
    >
      <Icon name={icon} size={24} color="#56703A" />
      <div className="flex flex-col gap-1">
        <span style={{ fontSize: 30, fontWeight: 700, letterSpacing: -0.5, lineHeight: 1.1 }}>{value}</span>
        <span style={{ fontSize: 13.5, color: "#55584E" }}>{labelText}</span>
      </div>
    </div>
  );
}

export function DemoNote({ children = "Sample values for design preview" }: { children?: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5" style={{ fontSize: 12.5, fontWeight: 600, color: "#686B60" }}>
      <Icon name="info" size={14} />
      {children}
    </span>
  );
}

export function Notice({ children, tone = "info", icon = "info" }: { children: ReactNode; tone?: Tone; icon?: IconName }) {
  return (
    <div className={`cs-note tone-${tone}`} role="note" style={{ borderColor: "transparent" }}>
      <Icon name={icon} size={18} />
      <div className="min-w-0">{children}</div>
    </div>
  );
}

export function ErrorBox({ error, onRetry }: { error: string; onRetry?: () => void }) {
  return (
    <div className="cs-note tone-bad" role="alert" style={{ borderColor: "transparent", alignItems: "center" }}>
      <Icon name="alert" size={18} />
      <span className="flex-1">{error}</span>
      {onRetry && (
        <Button small variant="secondary" icon="refresh" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}

export function Empty({ icon = "file", title, children }: { icon?: IconName; title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 py-10 text-center" style={{ color: "#55584E" }}>
      <span className="grid place-items-center rounded-full" style={{ width: 52, height: 52, background: "#EEF2E1", color: "#56703A" }}>
        <Icon name={icon} size={24} />
      </span>
      <strong style={{ color: "#20231D" }}>{title}</strong>
      {children && <div style={{ fontSize: 14 }}>{children}</div>}
    </div>
  );
}

export function Skeleton({ h = 18, w = "100%" }: { h?: number; w?: number | string }) {
  return <div className="cs-skel" style={{ height: h, width: w }} aria-hidden />;
}

export function LoadingBlock({ rows = 4 }: { rows?: number }) {
  return (
    <div className="flex flex-col gap-3" role="status" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} h={i === 0 ? 26 : 18} w={i === 0 ? "40%" : "100%"} />
      ))}
    </div>
  );
}

export function Backlink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link href={href} className="inline-flex items-center gap-1.5 no-underline" style={{ fontSize: 14, fontWeight: 600 }}>
      <Icon name="back" size={16} />
      {children}
    </Link>
  );
}

export function TextLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link href={href} className="inline-flex items-center gap-1 no-underline" style={{ fontSize: 14, fontWeight: 600 }}>
      {children}
      <Icon name="chev" size={15} />
    </Link>
  );
}

/* ---------------------------------------------------------------- Form fields */
type FieldWrap = { label: string; error?: string; hint?: ReactNode; className?: string };

export function TextField({ label: l, error, hint, className = "", ...rest }: FieldWrap & InputHTMLAttributes<HTMLInputElement>) {
  const id = useId();
  return (
    <div className={`flex flex-col gap-1.5 min-w-0 ${className}`}>
      <label htmlFor={id} className="cs-label">
        {l}
      </label>
      <input
        id={id}
        className="cs-input"
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-e` : undefined}
        {...rest}
      />
      {hint && <span style={{ fontSize: 12.5, color: "#686B60" }}>{hint}</span>}
      {error && (
        <span id={`${id}-e`} className="cs-field-error">
          {error}
        </span>
      )}
    </div>
  );
}

export function TextArea({ label: l, error, hint, className = "", ...rest }: FieldWrap & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const id = useId();
  return (
    <div className={`flex flex-col gap-1.5 min-w-0 ${className}`}>
      <label htmlFor={id} className="cs-label">
        {l}
      </label>
      <textarea id={id} className="cs-textarea" aria-invalid={error ? true : undefined} {...rest} />
      {hint && <span style={{ fontSize: 12.5, color: "#686B60" }}>{hint}</span>}
      {error && <span className="cs-field-error">{error}</span>}
    </div>
  );
}

export function SelectField({ label: l, error, className = "", children, ...rest }: FieldWrap & SelectHTMLAttributes<HTMLSelectElement>) {
  const id = useId();
  return (
    <div className={`flex flex-col gap-1.5 min-w-0 ${className}`}>
      <label htmlFor={id} className="cs-label">
        {l}
      </label>
      <select id={id} className="cs-select" {...rest}>
        {children}
      </select>
      {error && <span className="cs-field-error">{error}</span>}
    </div>
  );
}

export function SearchBox({
  value,
  onChange,
  placeholder,
  label: l = "Search",
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  label?: string;
}) {
  const id = useId();
  return (
    <div className="flex flex-col gap-1.5 min-w-0 flex-1">
      <label htmlFor={id} className="cs-label">
        {l}
      </label>
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "#686B60" }}>
          <Icon name="search" size={16} />
        </span>
        <input
          id={id}
          type="search"
          className="cs-input"
          style={{ paddingLeft: 36 }}
          value={value}
          placeholder={placeholder}
          onChange={(e) => onChange(e.target.value)}
        />
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- Modal */
export function Modal({
  open,
  title,
  onClose,
  children,
  footer,
  wide,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog
      ref={ref}
      onClose={onClose}
      aria-label={title}
      className="m-auto rounded-[14px] border border-line p-0 backdrop:bg-[rgba(32,35,29,.35)]"
      style={{ width: wide ? "min(760px, calc(100vw - 32px))" : "min(520px, calc(100vw - 32px))", maxHeight: "calc(100vh - 48px)" }}
    >
      {open && (
        <div className="flex flex-col">
          <div className="flex items-center justify-between gap-3 px-6 pt-5 pb-3">
            <h2 className="cs-h2">{title}</h2>
            <IconButton icon="x" label="Close" onClick={onClose} />
          </div>
          <div className="px-6 pb-5 overflow-y-auto">{children}</div>
          {footer && <div className="flex flex-wrap justify-end gap-2.5 px-6 py-4 border-t border-line cs-acts">{footer}</div>}
        </div>
      )}
    </dialog>
  );
}

/* ---------------------------------------------------------------- Helpers */
export function fmtDate(iso?: string | null, withTime = false): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  });
}

export function initials(name?: string | null): string {
  return (
    (name || "?")
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((p) => p[0]?.toUpperCase())
      .join("") || "?"
  );
}

export const CATEGORY_LABELS: Record<string, string> = {
  beverages: "Packaged Beverages",
  snacks: "Snacks",
  dairy: "Dairy",
  staples: "Food Staples",
  all: "All categories",
};
