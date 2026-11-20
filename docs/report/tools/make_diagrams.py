"""Generates the report/slide diagrams as SVG (CRATE-SCAN palette). Rendered to PNG by render_diagrams.mjs."""

from __future__ import annotations

import pathlib
from html import escape

OUT = pathlib.Path(__file__).resolve().parents[1] / "assets" / "diagrams"
OUT.mkdir(parents=True, exist_ok=True)

PAGE, SURF, BORDER = "#fbf8f0", "#ffffff", "#d8d6c9"
GREEN, GREEN_D, SOFT, TINT, SAGE = "#56703a", "#3e5228", "#e3eacf", "#eef2e1", "#c5d89d"
TEXT, TEXT2 = "#20231d", "#55584e"
WARN_BG, WARN_FG, INFO_BG, INFO_FG, BAD_BG, BAD_FG = "#fbefd9", "#7a4808", "#e2e8ee", "#2f4a63", "#f3dcd6", "#86301e"
FONT = "Inter, 'DejaVu Sans', Arial, sans-serif"


class Svg:
    def __init__(self, w: int, h: int, title: str = "") -> None:
        self.w, self.h, self.parts = w, h, []
        self.parts.append(f'<rect width="{w}" height="{h}" fill="{PAGE}"/>')
        if title:
            self.text(40, 52, title, 30, GREEN_D, 800)

    def raw(self, s: str) -> None:
        self.parts.append(s)

    def rect(self, x, y, w, h, fill=SURF, stroke=BORDER, r=14, sw=1.6, dash=False) -> None:
        d = ' stroke-dasharray="7 6"' if dash else ""
        self.raw(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def text(self, x, y, s, size=16, fill=TEXT, weight=500, anchor="start", italic=False) -> None:
        st = ' font-style="italic"' if italic else ""
        self.raw(f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{st}>{escape(s)}</text>')

    def lines(self, x, y, items, size=15, fill=TEXT2, weight=500, anchor="start", gap=1.45) -> None:
        for i, s in enumerate(items):
            self.text(x, y + i * size * gap, s, size, fill, weight, anchor)

    def box(self, x, y, w, h, title, sub=(), fill=SURF, stroke=BORDER, tfill=TEXT, size=17, subsize=14, center=False) -> None:
        self.rect(x, y, w, h, fill, stroke)
        cx = x + w / 2 if center else x + 18
        anc = "middle" if center else "start"
        self.text(cx, y + 30, title, size, tfill, 700, anc)
        self.lines(cx, y + 30 + subsize * 1.6, list(sub), subsize, TEXT2, 500, anc)

    def chip(self, x, y, w, label, fill=TINT, fg=GREEN_D, h=30, size=13.5) -> None:
        self.rect(x, y, w, h, fill, "none", r=h / 2, sw=0)
        self.text(x + w / 2, y + h / 2 + size * 0.35, label, size, fg, 700, "middle")

    def arrow(self, x1, y1, x2, y2, label="", color=GREEN, dash=False, both=False, lx=None, ly=None, size=13) -> None:
        d = ' stroke-dasharray="6 5"' if dash else ""
        self.raw(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="2.4"{d} marker-end="url(#ah)"' + (' marker-start="url(#ahs)"' if both else "") + "/>")
        if label:
            mx = lx if lx is not None else (x1 + x2) / 2
            my = ly if ly is not None else (y1 + y2) / 2 - 8
            self.text(mx, my, label, size, TEXT2, 600, "middle")

    def poly(self, pts, color=GREEN, dash=False, label="", lx=0, ly=0) -> None:
        d = ' stroke-dasharray="6 5"' if dash else ""
        p = " ".join(f"{a},{b}" for a, b in pts)
        self.raw(f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="2.4"{d} marker-end="url(#ah)"/>')
        if label:
            self.text(lx, ly, label, 13, TEXT2, 600, "middle")

    def save(self, name: str) -> None:
        defs = (f'<defs><marker id="ah" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto"><path d="M1,1 L11,6 L1,11 z" fill="{GREEN}"/></marker>'
                f'<marker id="ahs" markerWidth="12" markerHeight="12" refX="2" refY="6" orient="auto"><path d="M11,1 L1,6 L11,11 z" fill="{GREEN}"/></marker></defs>')
        body = "\n".join(self.parts)
        (OUT / f"{name}.svg").write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}">{defs}\n{body}\n</svg>')


def architecture() -> None:
    s = Svg(1700, 960, "System architecture")
    # users
    s.box(40, 190, 250, 150, "Users", ["Inspector (phone or desktop)", "Admin / Super Admin"], SOFT, GREEN, GREEN_D, center=True)
    # frontend
    s.rect(380, 120, 420, 640, TINT, SAGE, r=22)
    s.text(406, 156, "Frontend — Render web service", 17, GREEN_D, 800)
    s.text(406, 180, "Next.js 16 · React 19 · TypeScript · Tailwind 4", 14, TEXT2, 600)
    for i, (a, b) in enumerate([("Landing & Google sign-in", "Firebase Web SDK popup"), ("Inspection workflow", "photos → verify → review → report"),
                                 ("Ask AI assistant", "history + optional web research"), ("Admin console", "users, reference data, rules"),
                                 ("Analytics & Audit logs", "charts, filters, CSV/XLSX export"), ("System diagnostics", "live checks of every dependency")]):
        s.box(406, 205 + i * 90, 368, 74, a, [b], SURF, BORDER, size=16, subsize=13)
    # backend
    s.rect(960, 120, 400, 640, SURF, GREEN, r=22, sw=2.4)
    s.text(986, 156, "Backend API — Render web service", 17, GREEN_D, 800)
    s.text(986, 180, "FastAPI · Python 3.12 · Pydantic v2", 14, TEXT2, 600)
    layers = [("Security middleware", "rate limit · CORS · body size · headers"), ("Auth dependency", "verify Firebase ID token · role · status"),
              ("Routers (78 routes)", "typed request/response models"), ("Services", "workflow · compliance · matching · PDF"),
              ("Data-access layer", "owner-scoped queries · GridFS"), ("AI provider chain", "Gemini → NVIDIA → OCR fallback")]
    for i, (a, b) in enumerate(layers):
        s.box(986, 205 + i * 90, 348, 74, a, [b], TINT if i in (0, 1) else SURF, BORDER, size=16, subsize=13)
    # externals
    s.box(1460, 140, 220, 160, "MongoDB Atlas", ["documents + GridFS", "validators, indexes,", "migrations"], WARN_BG, "#d9b779", WARN_FG, center=True)
    s.box(1460, 345, 220, 150, "Firebase Auth", ["Google sign-in (browser)", "ID tokens + custom", "claims (role)"], INFO_BG, "#a9bccd", INFO_FG, center=True)
    s.box(1460, 540, 220, 170, "AI providers", ["Gemini (primary)", "NVIDIA (backup)", "PaddleOCR (optional)"], SOFT, GREEN, GREEN_D, center=True)
    # arrows
    s.arrow(290, 265, 380, 265, "HTTPS", both=True)
    s.arrow(800, 330, 960, 330, "REST + Bearer ID token", both=True, ly=312)
    s.arrow(1360, 220, 1460, 220, "queries", both=True)
    s.arrow(1360, 420, 1460, 420, "verify token", both=True, ly=402)
    s.arrow(1360, 625, 1460, 625, "label reading", both=True, ly=607)
    # CI/CD
    s.box(380, 810, 980, 90, "GitHub → Actions CI/CD → Render auto-deploy", ["Quality · Tests · Security scans · Build on every push; deploy from protected main after checks pass"], SOFT, GREEN, GREEN_D, center=True)
    s.arrow(870, 810, 870, 762)
    s.text(900, 792, "deploys both services", 13, TEXT2, 600)
    s.save("architecture")


def use_case() -> None:
    s = Svg(1700, 1020, "Use-case diagram")
    s.rect(330, 90, 1000, 890, SURF, BORDER, r=24, dash=True)
    s.text(360, 124, "CRATE-SCAN", 18, GREEN_D, 800)

    def actor(cx, cy, label, fg):
        s.raw(f'<circle cx="{cx}" cy="{cy}" r="22" fill="{fg}"/><rect x="{cx - 28}" y="{cy + 28}" width="56" height="64" rx="18" fill="{fg}"/>')
        s.text(cx, cy + 128, label, 18, fg, 800, "middle")

    actor(150, 250, "Inspector", GREEN_D)
    actor(1520, 330, "Admin", INFO_FG)
    actor(1520, 690, "Super Admin", WARN_FG)
    ins = ["Sign in with Google", "Capture / upload label photos", "Verify and correct fields", "Compliance analysis", "Review findings",
           "Record decision", "Download PDF report", "Submit product proposal", "AI label reading (+ retry)", "Ask AI assistant"]
    for i, t in enumerate(ins):
        y = 150 + i * 80
        s.rect(370, y, 420, 54, SOFT, GREEN, r=27, sw=1.4)
        s.text(580, y + 33, t, 16, GREEN_D, 700, "middle")
        s.arrow(214, 290, 370, y + 27, color=GREEN)
    adm = ["Approve / decline users", "Manage reference database", "Manage compliance rules", "Review proposals", "Analytics & audit logs", "System diagnostics", "Site settings & limits"]
    for i, t in enumerate(adm):
        y = 150 + i * 88
        s.rect(860, y, 420, 56, INFO_BG, "#a9bccd", r=28, sw=1.4)
        s.text(1070, y + 35, t, 16, INFO_FG, 700, "middle")
        s.arrow(1470, 370, 1280, y + 28, color=INFO_FG)
    s.rect(860, 790, 420, 56, WARN_BG, "#d9b779", r=28, sw=1.4)
    s.text(1070, 825, "Manage administrators", 16, WARN_FG, 700, "middle")
    s.arrow(1470, 730, 1280, 818, color=WARN_FG)
    s.arrow(1520, 640, 1520, 520, dash=True, color=TEXT2)
    s.text(1530, 585, "includes all Admin rights", 13, TEXT2, 600)
    s.rect(40, 800, 240, 150, SURF, BORDER)
    s.text(160, 840, "AI providers", 17, TEXT, 800, "middle")
    s.lines(160, 872, ["Gemini · NVIDIA", "label reading and", "assistant answers"], 14, TEXT2, 500, "middle")
    s.arrow(280, 850, 370, 790, dash=True, color=TEXT2)
    s.arrow(280, 890, 370, 870, dash=True, color=TEXT2)
    s.save("use_case")


def data_model() -> None:
    s = Svg(1700, 1000, "Data model (MongoDB collections)")
    cards = [
        (40, 100, 380, 230, "users", ["_id (Firebase uid) · email · name", "role: inspector | admin | super_admin", "status: pending | active | disabled | declined", "designation · office · created_at"], INFO_BG, INFO_FG),
        (40, 370, 380, 170, "user_invites", ["_id (email) · role · created_by", "accepted on first verified sign-in"], INFO_BG, INFO_FG),
        (40, 580, 380, 170, "usage_metrics", ["uid · day · ai_calls", "atomic daily AI quota per inspector"], INFO_BG, INFO_FG),
        (40, 790, 380, 160, "settings · counters", ["settings: one global document", "counters: CS-year and REF numbers"], "#eceae2", "#4d4f46"),
        (520, 100, 470, 360, "inspections", ["_id CS-2026-0001 · owner_uid · status", "category · photos[ ≤5 ] (GridFS ids)", "fields{ 22 label fields: value, AI value,", "   confidence, status, flag }", "findings[ rule, severity, decision ]", "analysis (matched reference) · decision", "report (PDF id, number)"], SOFT, GREEN_D),
        (520, 500, 470, 170, "inspection_notes · chat_messages", ["owner_uid · inspection_id · text", "chat: role, web flag, sources, provider"], SOFT, GREEN_D),
        (520, 710, 470, 240, "product_proposals", ["_id · owner_uid · inspection_id", "product{ name, brand, category … }", "status: pending | info_requested | approved", "reviews[ ] · messages[ ]"], SOFT, GREEN_D),
        (1090, 100, 570, 260, "reference_records (DEMO)", ["_id REF-0001 · product · brand · variant", "manufacturer{ name, address, state }", "licence{ number, validity, status }", "package_sizes · packaging images (GridFS)"], WARN_BG, WARN_FG),
        (1090, 400, 570, 240, "compliance_rules (versioned)", ["code DR-LB-01 … · category · check_type", "requirement · regulatory reference", "severity · status · version · history[ ]"], WARN_BG, WARN_FG),
        (1090, 680, 570, 270, "audit_logs + GridFS stores", ["audit_logs: actor · action · record · changes", "(append-only: no update or delete API)", "GridFS: photos · reports · refimages ·", "siteimages (originals deleted after report)"], "#eceae2", "#4d4f46"),
    ]
    for x, y, w, h, t, rows, fill, fg in cards:
        s.rect(x, y, w, h, fill, fg, r=16, sw=1.8)
        s.text(x + 20, y + 36, t, 19, fg, 800)
        s.lines(x + 20, y + 68, rows, 14.5, TEXT, 500)
    s.arrow(420, 220, 520, 220, "1 : N", both=True)
    s.arrow(755, 460, 755, 500, "1 : N", both=True, lx=800)
    s.arrow(755, 670, 755, 710, "1 : N", both=True, lx=800)
    s.arrow(990, 230, 1090, 230, "matched", dash=True)
    s.arrow(990, 330, 1090, 480, "checked against", dash=True, lx=1100, ly=395)
    s.arrow(230, 370, 230, 330, "accepted into", dash=True, lx=300, ly=358)
    s.arrow(1100, 830, 990, 830, "records", dash=True, lx=1045, ly=815)
    s.save("data_model")


def workflow() -> None:
    s = Svg(1700, 760, "Inspection workflow")
    steps = [("1  Photographs", ["Up to 5 photos,", "front / back / sides,", "quality check"]), ("2  AI reading", ["22 label fields with", "confidence per field", "(Gemini → NVIDIA → OCR)"]),
             ("3  Verify fields", ["Confirm or correct;", "format checks (FSSAI,", "dates, EAN, quantity)"]), ("4  Analysis", ["Match reference record,", "apply compliance rules,", "compare packaging"]),
             ("5  Findings", ["Accept, dismiss or", "correct each finding", "with a note"]), ("6  Decision & report", ["Verified / not verified /", "suspicious; 13-section PDF;", "originals deleted"])]
    for i, (t, sub) in enumerate(steps):
        x = 40 + i * 275
        s.rect(x, 130, 245, 210, SURF if i % 2 else SOFT, GREEN, r=18, sw=1.8)
        s.raw(f'<circle cx="{x + 34}" cy="{130 + 36}" r="0" fill="{GREEN}"/>')
        s.text(x + 20, 172, t, 18, GREEN_D, 800)
        s.lines(x + 20, 208, sub, 14.5, TEXT2, 500)
        if i < 5:
            s.arrow(x + 245, 235, x + 275, 235)
    s.rect(300, 420, 570, 150, WARN_BG, "#d9b779", r=16)
    s.text(322, 456, "If every AI provider fails", 17, WARN_FG, 800)
    s.lines(322, 488, ["Photos are saved; the inspection is marked incomplete.", "Inspector can retry now or later, or change photos.", "Optional offline OCR gives low-confidence draft fields."], 14.5, TEXT, 500)
    s.arrow(590, 340, 590, 420, "AI error", color=WARN_FG, ly=392, lx=640)
    s.rect(950, 420, 710, 150, INFO_BG, "#a9bccd", r=16)
    s.text(972, 456, "Human stays in control", 17, INFO_FG, 800)
    s.lines(972, 488, ["AI only suggests: every field and finding is confirmed by the inspector.", "Final classification is the inspector's decision; the report says so.", "Reference records and rules are labelled DEMO data."], 14.5, TEXT, 500)
    s.arrow(1300, 340, 1300, 420, "decision support only", color=INFO_FG, ly=392, lx=1390)
    s.rect(40, 620, 1620, 90, SOFT, GREEN, r=16)
    s.text(70, 656, "Retention", 17, GREEN_D, 800)
    s.text(70, 686, "Originals stay in GridFS only until the report is generated, then they are deleted; abandoned inspections are cleaned up after the retention period. Only compressed copies live inside the PDF.", 14.5, TEXT2, 500)
    s.save("workflow")


def security_layers() -> None:
    s = Svg(1700, 820, "Request protection pipeline")
    steps = [("HTTPS + HSTS", ["TLS everywhere;", "strict transport headers"]), ("Rate limit", ["per client address;", "default / write / AI"]), ("CORS + body limits", ["exact origin allow-list;", "12 MB uploads, 413"]),
             ("Token check", ["Firebase ID token", "signature, audience, expiry"]), ("Account + role", ["active account;", "inspector / admin / super"]), ("Owner-scoped data", ["owner_uid inside every", "query; others get 404"]),
             ("Strict models", ["Pydantic: unknown", "fields rejected (422)"]), ("Audit trail", ["admin actions and", "decisions recorded"])]
    for i, (t, sub) in enumerate(steps):
        col, row = i % 4, i // 4
        x, y = 50 + col * 410, 130 + row * 240
        s.rect(x, y, 350, 170, SOFT if (col + row) % 2 == 0 else SURF, GREEN, r=18, sw=1.8)
        s.text(x + 22, y + 44, f"{i + 1}  {t}", 19, GREEN_D, 800)
        s.lines(x + 22, y + 84, sub, 15.5, TEXT2, 500)
        if col < 3:
            s.arrow(x + 350, y + 85, x + 410, y + 85)
    s.poly([(1575, 300), (1575, 335), (225, 335), (225, 368)], GREEN)
    s.rect(50, 620, 1600, 150, INFO_BG, "#a9bccd", r=16)
    s.text(76, 658, "Verified by an attacker-style suite (49 tests) run in CI", 18, INFO_FG, 800)
    s.lines(76, 692, ["Forged / expired / replayed tokens · role escalation · cross-user access (IDOR) · NoSQL operator injection · malicious uploads and pixel bombs ·",
                      "parallel-request races on the AI quota · X-Forwarded-For rate-limit spoofing · CORS, headers and production-mode checks."], 14.5, TEXT, 500)
    s.save("security_layers")


def cicd() -> None:
    s = Svg(1700, 620, "CI/CD pipeline (GitHub Actions → Render)")
    stages = [("Push / pull request", ["feature branch", "required for main"]), ("Quality", ["ruff · mypy strict", "ESLint · tsc · Prettier"]), ("Tests", ["pytest (89 % cov.)", "Vitest · Playwright", "attack suite"]),
              ("Security", ["gitleaks · pip-audit", "pnpm audit · Bandit", "CodeQL (Py + TS)"]), ("Build", ["production bundle", "secret scan of bundle", "API start check"]), ("Deploy", ["protected main →", "Render auto-deploy", "release check"])]
    for i, (t, sub) in enumerate(stages):
        x = 40 + i * 275
        s.rect(x, 130, 245, 210, SOFT if i in (1, 2, 3, 4) else SURF, GREEN, r=18, sw=1.8)
        s.text(x + 20, 172, t, 18, GREEN_D, 800)
        s.lines(x + 20, 208, sub, 14.5, TEXT2, 500)
        if i < 5:
            s.arrow(x + 245, 235, x + 275, 235)
    s.rect(40, 400, 800, 170, INFO_BG, "#a9bccd", r=16)
    s.text(62, 438, "Branch protection on main", 17, INFO_FG, 800)
    s.lines(62, 470, ["Pull request required · six status checks required", "No force push · no deletion · no bypass", "Dependabot + secret scanning + push protection"], 15, TEXT, 500)
    s.rect(880, 400, 780, 170, WARN_BG, "#d9b779", r=16)
    s.text(902, 438, "Hosting (Render)", 17, WARN_FG, 800)
    s.lines(902, 470, ["crate-scan-api (FastAPI) and crate-scan-web (Next.js)", "Deploy only after checks pass; migrations run in the build", "Free instances sleep when idle; the app shows a start-up banner"], 15, TEXT, 500)
    s.save("cicd")


if __name__ == "__main__":
    for fn in (architecture, use_case, data_model, workflow, security_layers, cicd):
        fn()
    print("diagrams written to", OUT)
