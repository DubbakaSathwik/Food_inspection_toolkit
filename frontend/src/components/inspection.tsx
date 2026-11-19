"use client";

import { useEffect, useRef, useState } from "react";
import { STEP_NAMES } from "@/lib/inspection";
import { Icon } from "./icon";
import { Button, Modal } from "./ui";

/** 5-step stepper (desktop) + compact "STEP n OF 5" card (mobile). */
export function Stepper({ current }: { current: 1 | 2 | 3 | 4 | 5 }) {
  return (
    <>
      <ol className="cs-step-f flex items-center gap-3 list-none m-0 p-0" aria-label="Inspection steps">
        {STEP_NAMES.map((name, i) => {
          const n = i + 1;
          const done = n < current;
          const on = n === current;
          return (
            <li key={name} className="flex items-center gap-2.5 flex-1 last:flex-none min-w-0" aria-current={on ? "step" : undefined}>
              <span
                className="grid place-items-center shrink-0 rounded-full"
                style={{
                  width: 26,
                  height: 26,
                  fontSize: 12.5,
                  fontWeight: 700,
                  background: on ? "#56703A" : done ? "#E3EACF" : "#fff",
                  color: on ? "#fff" : done ? "#3B5420" : "#686B60",
                  border: on || done ? "none" : "1px solid #D8D6C9",
                }}
              >
                {done ? <Icon name="tick" size={14} /> : n}
              </span>
              <span style={{ fontSize: 14, fontWeight: on ? 700 : 500, color: on ? "#20231D" : "#55584E", whiteSpace: "nowrap" }}>
                {name}
              </span>
              {n < 5 && <span aria-hidden className="flex-1 h-px min-w-4" style={{ background: done ? "#9CAB84" : "#D8D6C9" }} />}
            </li>
          );
        })}
      </ol>
      <div className="cs-step-c cs-panel" style={{ padding: 16 }}>
        <div className="flex items-center justify-between gap-3">
          <span style={{ fontSize: 12.5, fontWeight: 700, letterSpacing: 1, color: "#55584E" }}>STEP {current} OF 5</span>
          <span style={{ fontSize: 15, fontWeight: 700, color: "#56703A" }}>{STEP_NAMES[current - 1]}</span>
        </div>
        <div
          className="mt-3 h-1.5 rounded-full"
          style={{ background: "#EEF2E1" }}
          role="progressbar"
          aria-valuemin={1}
          aria-valuemax={5}
          aria-valuenow={current}
        >
          <div
            className="h-1.5 rounded-full"
            style={{ width: `${(current / 5) * 100}%`, background: "#56703A", transition: "width .4s ease" }}
          />
        </div>
      </div>
    </>
  );
}

/** AI working animation (orbit + scan + progress steps). Pinned near the top, runs while `active`. */
export function AIWorkingOverlay({
  title,
  steps,
  active,
  interval = 1600,
}: {
  title: string;
  steps: string[];
  active: boolean;
  interval?: number;
}) {
  return active ? <OverlayBody title={title} steps={steps} interval={interval} /> : null;
}

function OverlayBody({ title, steps, interval }: { title: string; steps: string[]; interval: number }) {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const t = window.setInterval(() => setStep((s) => Math.min(s + 1, steps.length - 1)), interval);
    return () => window.clearInterval(t);
  }, [steps.length, interval]);
  return (
    <div
      className="fixed inset-0 z-[9000] flex justify-center items-start pt-[12vh] px-4"
      style={{ background: "rgba(246,242,230,.86)", animation: "csFade .2s ease both" }}
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div
        className="w-full max-w-[460px] rounded-[16px] border border-line bg-white p-7 flex flex-col items-center gap-5 shadow-xl"
        aria-live="polite"
      >
        <div className="relative" style={{ width: 96, height: 96 }} aria-hidden>
          <div
            className="absolute inset-0 rounded-full"
            style={{ border: "2px dashed #C5D89D", animation: "csOrbit 6s linear infinite" }}
          />
          <div
            className="absolute rounded-full"
            style={{ inset: 14, background: "#EEF2E1", animation: "csPulse 1.8s ease-in-out infinite" }}
          />
          <div className="absolute grid place-items-center" style={{ inset: 0, color: "#56703A" }}>
            <Icon name="scan" size={34} />
          </div>
          <div
            className="absolute left-3 right-3 h-0.5 rounded"
            style={{ background: "#56703A", animation: "csScan 2.2s ease-in-out infinite" }}
          />
        </div>
        <h2 className="cs-h2 text-center">
          {title}
          <span className="cs-dots">
            <span>.</span>
            <span>.</span>
            <span>.</span>
          </span>
        </h2>
        <ol className="w-full list-none m-0 p-0 flex flex-col gap-2.5">
          {steps.map((s, i) => (
            <li
              key={s}
              className="flex items-center gap-2.5"
              style={{ fontSize: 14, color: i <= step ? "#20231D" : "#9a9c92", fontWeight: i === step ? 700 : 500 }}
            >
              {i < step ? (
                <Icon name="check" size={17} color="#56703A" />
              ) : i === step ? (
                <span className="cs-ring" style={{ width: 16, height: 16, borderWidth: 2 }} />
              ) : (
                <span style={{ width: 16, height: 16, borderRadius: 8, border: "1.5px solid #D8D6C9" }} />
              )}
              {s}
            </li>
          ))}
        </ol>
        <p className="m-0 text-center" style={{ fontSize: 12.5, color: "#686B60" }}>
          This can take up to a minute. Please keep this page open.
        </p>
      </div>
    </div>
  );
}

type Rect = { x: number; y: number; w: number; h: number };

/** Drag a rectangle on the photo; fractions are stored, the original is never modified. */
export function CropDialog({
  open,
  src,
  initial,
  onClose,
  onSave,
  onClear,
}: {
  open: boolean;
  src: string | null;
  initial?: Rect | null;
  onClose: () => void;
  onSave: (r: Rect) => void;
  onClear: () => void;
}) {
  return (
    <Modal open={open} title="Crop photograph" onClose={onClose} wide>
      {open && <CropBody src={src} initial={initial} onSave={onSave} onClear={onClear} />}
    </Modal>
  );
}

function CropBody({
  src,
  initial,
  onSave,
  onClear,
}: {
  src: string | null;
  initial?: Rect | null;
  onSave: (r: Rect) => void;
  onClear: () => void;
}) {
  const box = useRef<HTMLDivElement>(null);
  const [rect, setRect] = useState<Rect | null>(initial ?? null);
  const start = useRef<{ x: number; y: number } | null>(null);
  const pos = (e: React.PointerEvent) => {
    const r = box.current!.getBoundingClientRect();
    return { x: Math.min(Math.max((e.clientX - r.left) / r.width, 0), 1), y: Math.min(Math.max((e.clientY - r.top) / r.height, 0), 1) };
  };
  const valid = rect && rect.w > 0.05 && rect.h > 0.05;
  return (
    <>
      <p className="mt-0" style={{ fontSize: 13.5, color: "#55584E" }}>
        Drag over the label area to use for analysis. The original photograph is kept unchanged as evidence.
      </p>
      <div
        ref={box}
        className="relative select-none touch-none mx-auto"
        style={{ maxWidth: 640, cursor: "crosshair" }}
        onPointerDown={(e) => {
          (e.target as HTMLElement).setPointerCapture(e.pointerId);
          const p = pos(e);
          start.current = p;
          setRect({ ...p, w: 0, h: 0 });
        }}
        onPointerMove={(e) => {
          if (!start.current) return;
          const p = pos(e);
          const s = start.current;
          setRect({ x: Math.min(s.x, p.x), y: Math.min(s.y, p.y), w: Math.abs(p.x - s.x), h: Math.abs(p.y - s.y) });
        }}
        onPointerUp={() => {
          start.current = null;
        }}
      >
        {src ? (
          // eslint-disable-next-line @next/next/no-img-element -- blob URL from the authenticated API
          <img src={src} alt="Photograph to crop" className="block w-full" draggable={false} />
        ) : (
          <div className="cs-skel" style={{ height: 300 }} />
        )}
        {rect && (
          <div
            className="absolute"
            style={{
              left: `${rect.x * 100}%`,
              top: `${rect.y * 100}%`,
              width: `${rect.w * 100}%`,
              height: `${rect.h * 100}%`,
              border: "2px solid #56703A",
              boxShadow: "0 0 0 9999px rgba(32,35,29,.45)",
            }}
          />
        )}
      </div>
      <div className="flex flex-wrap justify-end gap-2.5 mt-4 cs-acts">
        <Button variant="secondary" onClick={onClear}>
          Use full photo
        </Button>
        <Button disabled={!valid} onClick={() => rect && onSave(rect)}>
          Save crop
        </Button>
      </div>
    </>
  );
}
