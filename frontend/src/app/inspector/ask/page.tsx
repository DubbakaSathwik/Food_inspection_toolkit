"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Icon, type IconName } from "@/components/icon";
import { PageHeader } from "@/components/shell";
import { Button, ErrorBox, IconButton, LoadingBlock, Panel } from "@/components/ui";
import { api, errorMessage, type ChatMessage, type InspectionSummary, type Page } from "@/lib/api";

const SUGGESTIONS = [
  "Which allergens must be declared for muesli with nuts?",
  "Why was the manufacturer address a partial match?",
  "What should I check before marking a product suspicious?",
];

export default function AskAIPage() {
  const [msgs, setMsgs] = useState<ChatMessage[] | null>(null);
  const [draft, setDraft] = useState("");
  const [web, setWeb] = useState(false);
  const [ctx, setCtx] = useState(() =>
    typeof window === "undefined" ? "" : (new URLSearchParams(window.location.search).get("inspection") ?? ""),
  );
  const [recent, setRecent] = useState<InspectionSummary[]>([]);
  const [sending, setSending] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const end = useRef<HTMLDivElement>(null);

  const load = useCallback(() => {
    api<Page<ChatMessage>>("/api/v1/assistant/messages", { query: { page_size: 100 } })
      .then((p) => setMsgs(p.items))
      .catch((e) => setErr(errorMessage(e)));
  }, []);
  useEffect(() => {
    load();
    api<Page<InspectionSummary>>("/api/v1/inspections", { query: { page_size: 20 } })
      .then((p) => setRecent(p.items))
      .catch(() => undefined);
  }, [load]);
  useEffect(() => {
    end.current?.scrollIntoView({ block: "end" });
  }, [msgs, sending]);

  async function send(text: string) {
    const message = text.trim();
    if (!message || sending) return;
    setSending(true);
    setErr(null);
    setDraft("");
    try {
      const r = await api<{ user: ChatMessage; assistant: ChatMessage }>("/api/v1/assistant/messages", {
        method: "POST",
        body: { message, web, inspection_id: ctx || undefined },
      });
      setMsgs((m) => [...(m ?? []), r.user, r.assistant]);
    } catch (e) {
      setErr(errorMessage(e));
      setDraft(message);
    } finally {
      setSending(false);
    }
  }
  async function clear() {
    try {
      await api("/api/v1/assistant/messages", { method: "DELETE" });
      setMsgs([]);
    } catch (e) {
      setErr(errorMessage(e));
    }
  }

  const sees: [IconName, string][] = [
    ["scan", "The selected inspection and its photographs"],
    ["box", "The demonstration reference database"],
    ["rules", "The demo labelling rules"],
    ["history", "Your own past inspection reports"],
    ["link", "Official sources, only when you ask"],
  ];
  return (
    <>
      <PageHeader title="Ask AI" subtitle="Questions about inspections, findings and labelling requirements." />
      <div className="grid grid-cols-[minmax(0,1fr)_300px] gap-5 items-start max-[960px]:grid-cols-1">
        <section className="cs-panel flex flex-col p-0 overflow-hidden" style={{ padding: 0 }} aria-label="Inspection assistant">
          <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5 border-b border-line">
            <span className="flex items-center gap-2" style={{ fontWeight: 700 }}>
              <Icon name="chat" size={17} />
              Inspection assistant
            </span>
            <div className="flex flex-wrap items-center gap-2">
              <label className="cs-chipbtn" style={{ borderRadius: 10, background: web ? "#EEF2E1" : "#fff" }}>
                <input type="checkbox" checked={web} onChange={(e) => setWeb(e.target.checked)} className="accent-[#3E5228]" />
                Internet research {web ? "on" : "off"}
              </label>
              <Button small variant="secondary" onClick={() => void clear()} disabled={!msgs?.length}>
                Clear chat
              </Button>
            </div>
          </div>
          <div className="px-5 py-3 border-b border-line flex flex-wrap items-center gap-2" style={{ background: "#FBF8F0" }}>
            <label htmlFor="ctx" className="cs-label">
              Context
            </label>
            <select
              id="ctx"
              className="cs-select"
              style={{ width: "auto", minHeight: 36, padding: "4px 10px", fontSize: 13.5, maxWidth: "100%" }}
              value={ctx}
              onChange={(e) => setCtx(e.target.value)}
            >
              <option value="">General question (no inspection)</option>
              {recent.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.id} · {i.product_name || "Untitled"}
                </option>
              ))}
            </select>
          </div>
          <div
            className="flex flex-col gap-3 px-5 py-5 overflow-y-auto"
            style={{ minHeight: 320, maxHeight: "60vh", background: "#FBF8F0" }}
            aria-live="polite"
          >
            <div
              className="self-start max-w-[85%] rounded-[12px] border border-line bg-white px-4 py-3"
              style={{ fontSize: 14.5, lineHeight: 1.6 }}
            >
              Ask about an inspection you have run, a labelling requirement, or a finding you want explained. I can also search official
              sources when you turn on internet research.
            </div>
            {!msgs ? (
              <LoadingBlock rows={3} />
            ) : (
              msgs.map((m) => (
                <div
                  key={m.id}
                  className={`max-w-[85%] rounded-[12px] px-4 py-3 ${m.role === "user" ? "self-end" : "self-start border border-line bg-white"}`}
                  style={{
                    fontSize: 14.5,
                    lineHeight: 1.6,
                    whiteSpace: "pre-wrap",
                    overflowWrap: "anywhere",
                    ...(m.role === "user" ? { background: "#56703A", color: "#fff" } : {}),
                  }}
                >
                  {m.text}
                  {m.role === "assistant" && m.sources.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-line flex flex-col gap-1" style={{ fontSize: 12.5 }}>
                      <strong>Sources (web research — not an official finding)</strong>
                      {m.sources.map((s) => (
                        <a key={s.url} href={/^https?:\/\//i.test(s.url) ? s.url : "#"} target="_blank" rel="noopener noreferrer nofollow">
                          {s.title}
                        </a>
                      ))}
                    </div>
                  )}
                  {m.role === "user" && (m.web || m.inspection_id) && (
                    <div style={{ fontSize: 11.5, opacity: 0.85 }}>
                      {[m.web && "web research", m.inspection_id].filter(Boolean).join(" · ")}
                    </div>
                  )}
                </div>
              ))
            )}
            {sending && (
              <div className="self-start rounded-[12px] border border-line bg-white px-4 py-3" style={{ fontSize: 14 }}>
                Thinking
                <span className="cs-dots">
                  <span>.</span>
                  <span>.</span>
                  <span>.</span>
                </span>
              </div>
            )}
            <div ref={end} />
          </div>
          <div className="flex flex-col gap-3 px-5 py-4 border-t border-line">
            {err && <ErrorBox error={err} />}
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  className="cs-chipbtn"
                  style={{ borderRadius: 8, background: "#FBF8F0", fontWeight: 500, textAlign: "left" }}
                  onClick={() => void send(s)}
                >
                  {s}
                </button>
              ))}
            </div>
            <form
              className="flex items-center gap-2 rounded-[12px] border border-input p-1.5 pl-3"
              onSubmit={(e) => {
                e.preventDefault();
                void send(draft);
              }}
            >
              <label htmlFor="ask" className="sr-only">
                Your question
              </label>
              <input
                id="ask"
                className="flex-1 min-w-0 border-0 outline-none bg-transparent"
                style={{ fontSize: 14.5, minHeight: 36 }}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Ask about a finding, a rule, or a product…"
                maxLength={8000}
              />
              <IconButton
                icon="send"
                label="Send"
                disabled={!draft.trim() || sending}
                className="!bg-[#56703A] !text-white !border-[#56703A]"
                onClick={() => void send(draft)}
              />
            </form>
            <p className="m-0" style={{ fontSize: 12.5, color: "#686B60" }}>
              Answers are decision support, not a regulatory ruling. Internet research runs only when you switch it on.
            </p>
          </div>
        </section>
        <div className="flex flex-col gap-5">
          <Panel title="What the assistant can see">
            <ul className="list-none m-0 p-0 flex flex-col">
              {sees.map(([i, t]) => (
                <li key={t} className="flex gap-2.5 py-2.5 border-b border-line" style={{ fontSize: 13.5 }}>
                  <Icon name={i} size={16} />
                  {t}
                </li>
              ))}
            </ul>
            <p className="mb-0" style={{ fontSize: 12.5, color: "#55584E" }}>
              Your inspections stay private to your account. Other inspectors&apos; records are never used.
            </p>
          </Panel>
          <Panel title="Good things to ask">
            <ul className="m-0 pl-4 list-disc flex flex-col gap-1.5" style={{ fontSize: 13.5, color: "#55584E" }}>
              <li>Explain an ingredient or a nutrition panel</li>
              <li>Why a finding was raised and what evidence it used</li>
              <li>Which declarations apply to a food category</li>
              <li>What to ask a manufacturer during follow-up</li>
              <li>A summary of this inspection for your notes</li>
            </ul>
          </Panel>
        </div>
      </div>
    </>
  );
}
