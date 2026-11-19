"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/shell";
import { Button, Chip, ErrorBox, LoadingBlock, Notice, Panel } from "@/components/ui";
import { api, errorMessage, type S } from "@/lib/api";

type Info = S["DiagnosticInfo"];
type Result = S["DiagnosticOut"];

const TONE = { ok: "ok", warn: "warn", fail: "bad", skip: "neu" } as const;
const LABEL = { ok: "Working", warn: "Needs attention", fail: "Failing", skip: "Not tested" } as const;

export default function Diagnostics() {
  const [checks, setChecks] = useState<Info[] | null>(null);
  const [results, setResults] = useState<Record<string, Result>>({});
  const [running, setRunning] = useState<Record<string, boolean>>({});
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api<Info[]>("/api/v1/admin/diagnostics")
      .then(setChecks)
      .catch((e) => setErr(errorMessage(e)));
  }, []);

  async function run(id: string) {
    setRunning((r) => ({ ...r, [id]: true }));
    try {
      const res = await api<Result>(`/api/v1/admin/diagnostics/${id}`, { method: "POST" });
      setResults((r) => ({ ...r, [id]: res }));
    } catch (e) {
      setResults((r) => ({
        ...r,
        [id]: {
          id,
          title: id,
          status: "fail",
          detail: errorMessage(e),
          hints: ["The server did not answer. Is the backend running?"],
          ms: 0,
        },
      }));
    } finally {
      setRunning((r) => ({ ...r, [id]: false }));
    }
  }

  async function runAll() {
    if (!checks) return;
    await Promise.all(checks.map((c) => run(c.id)));
  }

  const anyRunning = Object.values(running).some(Boolean);
  const done = Object.values(results);
  const failing = done.filter((r) => r.status === "fail").length;
  const warning = done.filter((r) => r.status === "warn").length;

  return (
    <>
      <PageHeader
        title="System diagnostics"
        subtitle="Test the database, sign-in and every AI provider from here. Results show the real reason when something fails."
        actions={
          <Button icon="play" working={anyRunning} onClick={() => void runAll()}>
            Run all checks
          </Button>
        }
      />
      {err && <ErrorBox error={err} />}
      {!checks && !err && <LoadingBlock />}
      {checks && done.length === checks.length && (
        <Notice tone={failing ? "bad" : warning ? "warn" : "ok"} icon={failing || warning ? "alert" : "check"}>
          {failing
            ? `${failing} check${failing > 1 ? "s are" : " is"} failing. Fix the items marked “Failing”, restart the backend and run again.`
            : warning
              ? `${warning} item${warning > 1 ? "s need" : " needs"} attention.`
              : "Everything that is configured is working."}
        </Notice>
      )}
      <div className="flex flex-col gap-4 mt-4">
        {checks?.map((c) => {
          const r = results[c.id];
          return (
            <Panel
              key={c.id}
              title={c.title}
              action={
                <Button
                  small
                  variant="secondary"
                  icon="refresh"
                  working={!!running[c.id]}
                  onClick={() => void run(c.id)}
                  aria-label={`Test ${c.title}`}
                >
                  Test
                </Button>
              }
            >
              <p style={{ margin: 0, fontSize: 13.5, color: "#55584E" }}>{c.description}</p>
              {r && (
                <div className="mt-3 flex flex-col gap-2" role="status" aria-label={`${c.title} result`}>
                  <div className="flex items-center gap-2">
                    <Chip tone={TONE[r.status]}>{LABEL[r.status]}</Chip>
                    {r.ms > 0 && <span style={{ fontSize: 12.5, color: "#55584E" }}>{r.ms} ms</span>}
                  </div>
                  <div style={{ fontSize: 14, overflowWrap: "anywhere" }}>{r.detail}</div>
                  {r.hints.length > 0 && (
                    <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13.5 }}>
                      {r.hints.map((h) => (
                        <li key={h}>{h}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </Panel>
          );
        })}
      </div>
    </>
  );
}
