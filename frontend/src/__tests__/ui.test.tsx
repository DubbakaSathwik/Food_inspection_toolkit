import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Stepper } from "@/components/inspection";
import { REPORT_SECTIONS, ReportDocument } from "@/components/report";
import { Chip, label } from "@/components/ui";
import type { Inspection } from "@/lib/api";
import { nextStep } from "@/lib/inspection";

describe("Chip", () => {
  it("maps statuses to labels and tones (never colour alone)", () => {
    render(<Chip status="suspicious" />);
    const chip = screen.getByText("Suspicious");
    expect(chip.closest(".cs-chip")).toHaveClass("tone-warn");
    expect(label("not_verified")).toBe("Not verified");
    expect(label("super_admin")).toBe("Super Admin");
  });
});

describe("nextStep", () => {
  const base = { id: "CS-2026-0001", photo_count: 2, fields_extracted: 20, findings_open: 3 };
  it("routes each inspection state to the right screen", () => {
    expect(nextStep({ ...base, status: "draft" }).href).toBe("/inspector/new?id=CS-2026-0001");
    expect(nextStep({ ...base, status: "incomplete" }).href).toBe("/inspector/verify/CS-2026-0001");
    expect(nextStep({ ...base, status: "extracted" }).badge).toBe("Fields not checked");
    expect(nextStep({ ...base, status: "analysed" }).href).toBe("/inspector/findings/CS-2026-0001");
    expect(nextStep({ ...base, status: "completed" }).href).toBe("/inspector/report/CS-2026-0001");
  });
});

describe("Stepper", () => {
  it("marks the current step for assistive tech and shows the compact step", () => {
    render(<Stepper current={3} />);
    expect(screen.getByText("STEP 3 OF 5")).toBeInTheDocument();
    const current = document.querySelector('[aria-current="step"]');
    expect(current).toHaveTextContent("AI Review");
  });
});

describe("ReportDocument", () => {
  it("renders the 13 report sections in the fixed order with the signature disclaimer", () => {
    const d = {
      id: "CS-2026-0001",
      status: "completed",
      owner_name: "Ravi",
      created_at: "2026-11-19T10:00:00Z",
      photos: [],
      photos_deleted: true,
      category: "staples",
      extraction: { status: "done", attempts: [] },
      fields: [],
      analysis: null,
      findings: [],
      analysis_stale: false,
      suggestion: null,
      decision: { classification: "not_verified", remarks: "x" },
      report: null,
      notes: [],
      proposal_id: null,
    } as unknown as Inspection;
    render(<ReportDocument d={d} signature="Ravi Inspector" view="print" />);
    const headings = screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent);
    expect(headings).toEqual(REPORT_SECTIONS.map((s, i) => `${i + 1}. ${s}`));
    expect(screen.getByText(/not a certified digital signature/)).toBeInTheDocument();
  });
});

describe("Modal", () => {
  it("does not report a programmatic close as a user close (dialog switching regression)", async () => {
    const { Modal } = await import("@/components/ui");
    const onClose = vi.fn();
    const proto = HTMLDialogElement.prototype as unknown as { showModal: () => void; close: () => void };
    proto.showModal ??= function (this: HTMLDialogElement) {
      this.setAttribute("open", "");
    };
    proto.close ??= function (this: HTMLDialogElement) {
      this.removeAttribute("open");
      this.dispatchEvent(new Event("close"));
    };
    const { rerender } = render(
      <Modal open title="Menu" onClose={onClose}>
        x
      </Modal>,
    );
    rerender(
      <Modal open={false} title="Menu" onClose={onClose}>
        x
      </Modal>,
    );
    expect(onClose).not.toHaveBeenCalled();
  });
});
