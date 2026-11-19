import type { InspectionSummary } from "./api";

/** Where an inspection continues, and how its state is described (design "continue where you left off"). */
export function nextStep(i: Pick<InspectionSummary, "id" | "status" | "photo_count" | "fields_extracted" | "findings_open">): {
  href: string;
  action: string;
  badge: string;
  tone: "warn" | "neu" | "ok" | "bad";
  detail: string;
} {
  switch (i.status) {
    case "draft":
      return {
        href: `/inspector/new?id=${i.id}`,
        action: "Add photographs",
        badge: "Draft",
        tone: "neu",
        detail: `${i.photo_count} photograph${i.photo_count === 1 ? "" : "s"} added`,
      };
    case "incomplete":
      return {
        href: `/inspector/verify/${i.id}`,
        action: "Retry AI reading",
        badge: "AI reading failed",
        tone: "bad",
        detail: "Photographs saved — retry when the AI service is available",
      };
    case "extracted":
      return {
        href: `/inspector/verify/${i.id}`,
        action: "Verify fields",
        badge: "Fields not checked",
        tone: "warn",
        detail: `${i.fields_extracted} fields extracted`,
      };
    case "analysed":
      return {
        href: `/inspector/findings/${i.id}`,
        action: "Review findings",
        badge: "Awaiting your review",
        tone: "warn",
        detail: `Findings ready · ${i.findings_open} open`,
      };
    default:
      return { href: `/inspector/report/${i.id}`, action: "View report", badge: "Completed", tone: "ok", detail: "Report generated" };
  }
}

export const STEP_NAMES = ["Photographs", "Verify Fields", "AI Review", "Findings", "Report"] as const;
