"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Icon } from "@/components/icon";
import { ImageSlot } from "@/components/media";
import { PageHeader } from "@/components/shell";
import { ButtonLink, CATEGORY_LABELS, Chip, Empty, ErrorBox, fmtDate, LoadingBlock, Metric, Panel, TextLink } from "@/components/ui";
import { api, errorMessage, type S } from "@/lib/api";
import { nextStep } from "@/lib/inspection";

type Dash = S["DashboardOut"];

export default function InspectorDashboard() {
  const [d, setD] = useState<Dash | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const load = useCallback(() => {
    api<Dash>("/api/v1/inspector/dashboard")
      .then((x) => {
        setD(x);
        setErr(null);
      })
      .catch((e) => setErr(errorMessage(e)));
  }, []);
  useEffect(load, [load]);

  return (
    <>
      <PageHeader title="Inspector Dashboard" subtitle="Manage your inspections and review product findings." />
      {err && <ErrorBox error={err} onRetry={load} />}
      <div className="grid gap-4 cs-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))" }}>
        <Metric icon="doc" value={d ? d.total : "—"} labelText="Total Inspections" />
        <Metric icon="check" value={d ? d.completed : "—"} labelText="Completed Inspections" />
        <Metric icon="clock" value={d ? d.pending_reviews : "—"} labelText="Pending Reviews" />
        <Metric icon="proposal" value={d ? d.proposals : "—"} labelText="Submitted Proposals" />
      </div>

      <section
        className="flex flex-wrap items-stretch gap-4 rounded-[12px] border border-line p-4"
        style={{ background: "#E3EACF" }}
        aria-label="Start a new inspection"
      >
        <div className="flex flex-col justify-center gap-4 flex-[1_1_320px] p-6 max-[760px]:p-2">
          <h2 style={{ margin: 0, fontSize: 28, fontWeight: 800, letterSpacing: -0.4 }} className="max-[760px]:!text-[22px]">
            Start a New Inspection
          </h2>
          <p style={{ margin: 0, fontSize: 16, lineHeight: 1.6, color: "#55584E", maxWidth: 380 }}>
            Upload product photographs, check what the AI read, then review the findings.
          </p>
          <div>
            <ButtonLink href="/inspector/new" iconRight="arrow">
              Create Inspection
            </ButtonLink>
          </div>
        </div>
        <ImageSlot
          slot="banner"
          label="Banner photograph — packaged food products. Replace in Admin › Settings › Website Images."
          className="flex-[1_1_360px] min-h-[200px] max-[760px]:min-h-[150px]"
        />
      </section>

      <Panel title="Continue where you left off" action={<TextLink href="/inspector/history">All inspections</TextLink>}>
        {!d ? (
          <LoadingBlock rows={3} />
        ) : d.continue_items.length === 0 ? (
          <Empty icon="check" title="Nothing waiting">
            All your inspections are complete.
          </Empty>
        ) : (
          <div className="grid gap-3.5 cs-grid-1" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))" }}>
            {d.continue_items.map((i) => {
              const s = nextStep(i);
              return (
                <Link
                  key={i.id}
                  href={s.href}
                  className="cs-card flex flex-col gap-2.5 rounded-[11px] border border-line p-[18px] no-underline min-w-0"
                  style={{ background: "#FBF8F0", color: "#20231D" }}
                >
                  <span className="flex flex-wrap items-center justify-between gap-2">
                    <span style={{ fontSize: 12.5, fontWeight: 700, color: "#686B60" }}>{i.id}</span>
                    <Chip tone={s.tone} dot={false}>
                      {s.badge}
                    </Chip>
                  </span>
                  <span style={{ fontSize: 15, fontWeight: 700, lineHeight: 1.35, overflowWrap: "anywhere" }}>
                    {i.product_name || "Untitled product"}
                  </span>
                  <span style={{ fontSize: 13, color: "#55584E" }}>{s.detail}</span>
                  <span className="inline-flex items-center gap-1" style={{ fontSize: 13, fontWeight: 600, color: "#56703A" }}>
                    {s.action}
                    <Icon name="chev" size={15} />
                  </span>
                </Link>
              );
            })}
          </div>
        )}
      </Panel>

      <Panel title="Recent Inspections" action={<TextLink href="/inspector/history">View all history</TextLink>}>
        {!d ? (
          <LoadingBlock />
        ) : d.recent.length === 0 ? (
          <Empty title="No inspections yet">Create your first inspection to see it here.</Empty>
        ) : (
          <table className="cs-table">
            <thead>
              <tr>
                <th>Inspection ID</th>
                <th>Product Name</th>
                <th>Category</th>
                <th>Date</th>
                <th>Classification</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {d.recent.map((i) => {
                const s = nextStep(i);
                return (
                  <tr key={i.id}>
                    <td>
                      <span className="cs-cell-label">Inspection ID</span>
                      <span style={{ color: "#686B60", fontWeight: 600 }}>{i.id}</span>
                    </td>
                    <td>
                      <span className="cs-cell-label">Product</span>
                      <strong>{i.product_name || "Untitled product"}</strong>
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
                      {i.classification ? <Chip status={i.classification} /> : <Chip status={i.status} />}
                    </td>
                    <td>
                      <Link href={s.href} className="inline-flex items-center gap-1 no-underline" style={{ fontWeight: 600 }}>
                        View
                        <Icon name="chev" size={15} />
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Panel>
    </>
  );
}
