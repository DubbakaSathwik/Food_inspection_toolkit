"""Inspection report PDF (REQ-028) — fixed section order from the project details document §8.2."""

from __future__ import annotations

import io
from datetime import datetime
from html import escape as _html_escape
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.fields import CATEGORIES, FIELDS
from app.services.images import ImageInput, compress_for_pdf

SECTIONS = [
    "1. Inspection ID, date and time",
    "2. Inspector details",
    "3. Product and manufacturer details",
    "4. Original product photographs",
    "5. Complete extracted label information",
    "6. FSSAI licence verification (demo records)",
    "7. Manufacturer and reference database matching",
    "8. FSSAI compliance findings and rule evidence",
    "9. Packaging anomaly and suspicious-claim analysis",
    "10. AI confidence indicators",
    "11. Inspector corrections and comments",
    "12. Final inspector decision and remarks",
    "13. Sources, limitations and disclaimers",
]

GREEN = colors.HexColor("#56703A")
TEXT = colors.HexColor("#20231D")
MUTED = colors.HexColor("#686B60")
BORDER = colors.HexColor("#E5E4DA")
TINT = colors.HexColor("#EEF2E1")

CLASS_LABEL = {"verified": "Verified", "not_verified": "Not verified", "suspicious": "Suspicious"}


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "t",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            textColor=TEXT,
            alignment=TA_LEFT,
            spaceAfter=2,
        ),
        "h": ParagraphStyle(
            "h",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=GREEN,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "p": ParagraphStyle(
            "p",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=TEXT,
        ),
        "small": ParagraphStyle(
            "s",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=MUTED,
        ),
        "cell": ParagraphStyle(
            "c",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=TEXT,
        ),
        "cellb": ParagraphStyle(
            "cb",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=TEXT,
        ),
    }


def _t(text: Any) -> str:
    return _html_escape(str(text), quote=False) if text not in (None, "") else "—"


def _table(
    rows: list[list[Any]], widths: list[float], st: dict[str, ParagraphStyle], header: bool = True
) -> Table:
    data = [
        [
            Paragraph(_t(c), st["cellb"] if (header and i == 0) else st["cell"])
            if not isinstance(c, Paragraph)
            else c
            for c in row
        ]
        for i, row in enumerate(rows)
    ]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), TINT))
    t.setStyle(TableStyle(style))
    return t


def _kv(pairs: list[tuple[str, Any]], st: dict[str, ParagraphStyle]) -> Table:
    return _table([[k, v] for k, v in pairs], [50 * mm, 120 * mm], st, header=False)


def build_report(
    insp: dict[str, Any],
    originals: list[ImageInput],
    signature_name: str,
    generated_at: datetime,
    general: dict[str, Any],
) -> tuple[bytes, int]:
    st = _styles()
    buf = io.BytesIO()
    pages = {"n": 0}

    def on_page(canvas: Any, doc: Any) -> None:
        pages["n"] = doc.page
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(
            18 * mm,
            10 * mm,
            f"CRATE-SCAN inspection report {insp['_id']} — "
            f"{(general.get('report_footer') or '')[:120]}",
        )
        canvas.drawRightString(192 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title=f"Inspection report {insp['_id']}",
        author="CRATE-SCAN",
    )
    fields = insp.get("fields") or {}
    analysis = insp.get("analysis") or {}
    decision = insp.get("decision") or {}
    v = {k: (f or {}).get("value") for k, f in fields.items()}
    story: list[Any] = [
        Paragraph(
            _t(general.get("org_name") or "CRATE-SCAN") + " — Food Product Inspection Report",
            st["title"],
        ),
        Paragraph(
            "Decision-support report. Demo reference data. Not an official government verification or legal verdict.",
            st["small"],
        ),
    ]

    def h(i: int) -> None:
        story.append(Paragraph(SECTIONS[i], st["h"]))

    h(0)
    story.append(
        _kv(
            [
                ("Inspection ID", insp["_id"]),
                ("Created", insp["created_at"].strftime("%d %b %Y, %H:%M UTC")),
                ("Report generated", generated_at.strftime("%d %b %Y, %H:%M UTC")),
                ("Category", CATEGORIES.get(insp.get("category") or "", "—")),
            ],
            st,
        )
    )
    h(1)
    story.append(
        _kv([("Inspector", insp.get("owner_name")), ("Email", insp.get("owner_email"))], st)
    )
    h(2)
    story.append(
        _kv(
            [
                ("Product", v.get("product_name")),
                ("Brand", v.get("brand")),
                ("Variant", v.get("variant")),
                ("Net quantity", v.get("net_quantity")),
                ("Manufacturer", v.get("manufacturer_name")),
                ("Address", v.get("manufacturer_address")),
                ("FSSAI licence (as printed)", v.get("fssai_licence")),
            ],
            st,
        )
    )
    h(3)
    if originals:
        cells: list[Any] = []
        photos = insp.get("photos", [])
        for i, img in enumerate(originals):
            small = compress_for_pdf(img.data)
            reader = Image(io.BytesIO(small))
            ratio = reader.imageHeight / float(reader.imageWidth or 1)
            w = 80 * mm
            reader.drawWidth, reader.drawHeight = w, min(w * ratio, 95 * mm)
            if w * ratio > 95 * mm:
                reader.drawWidth = 95 * mm / ratio
            q = (photos[i].get("quality") if i < len(photos) else {}) or {}
            cap = f"Photo {i + 1} — {img.label or 'unlabelled'}" + (
                " · quality warning: " + "; ".join(q.get("issues", [])) if q.get("issues") else ""
            )
            cells.append(
                Table(
                    [[reader], [Paragraph(_t(cap), st["small"])]],
                    colWidths=[84 * mm],
                    style=[("LEFTPADDING", (0, 0), (-1, -1), 0)],
                )
            )
        grid = [
            cells[i : i + 2] + ([""] if len(cells[i : i + 2]) == 1 else [])
            for i in range(0, len(cells), 2)
        ]
        story.append(
            Table(grid, colWidths=[87 * mm, 87 * mm], style=[("VALIGN", (0, 0), (-1, -1), "TOP")])
        )
        story.append(
            Paragraph(
                "Embedded copies are compressed for the report; originals are deleted after generation.",
                st["small"],
            )
        )
    else:
        story.append(Paragraph("No photographs available.", st["p"]))
    h(4)
    rows: list[list[Any]] = [["Field", "Value (final)", "Source photo"]]
    for f in FIELDS:
        d = fields.get(f.key) or {}
        rows.append(
            [
                f.label,
                d.get("value"),
                f"Photo {d['source_photo']}" if d.get("source_photo") else "—",
            ]
        )
    story.append(_table(rows, [48 * mm, 100 * mm, 26 * mm], st))
    h(5)
    lic = analysis.get("licence") or {}
    story.append(
        _kv(
            [
                ("Result", lic.get("label")),
                ("Detail", lic.get("detail")),
                ("Demo record", lic.get("record_id")),
            ],
            st,
        )
    )
    h(6)
    ref = analysis.get("reference") or {}
    story.append(
        Paragraph(
            _t(f"Status: {(ref.get('status') or '').replace('_', ' ')} — {ref.get('detail', '')}"),
            st["p"],
        )
    )
    if ref.get("comparisons"):
        story.append(
            _table(
                [["Field", "Extracted", "Reference (demo)", "Result"]]
                + [
                    [r["field"], r["extracted"], r["reference"], r["result"]]
                    for r in ref["comparisons"]
                ],
                [38 * mm, 52 * mm, 52 * mm, 30 * mm],
                st,
            )
        )
    h(7)
    comp = (analysis.get("compliance") or {}).get("results", [])
    if comp:
        story.append(
            _table(
                [["Rule", "Requirement", "Result", "Reason / evidence"]]
                + [
                    [
                        f"{r['rule_code']} v{r['version']}\n{r['reference']}",
                        r["requirement"],
                        r["result"].replace("_", " "),
                        r["reason"] or "—",
                    ]
                    for r in comp
                ],
                [36 * mm, 56 * mm, 20 * mm, 60 * mm],
                st,
            )
        )
    else:
        story.append(Paragraph("No demo rules applied for this category.", st["p"]))
    h(8)
    pkg = analysis.get("packaging") or {}
    story.append(Paragraph(_t(pkg.get("summary")), st["p"]))
    obs_rows = [["Area", "Observation", "Severity"]] + [
        [o["area"], o["observation"], o["severity"]] for o in pkg.get("observations", [])
    ]
    claims = [r for r in comp if r.get("claim") and r["result"] == "review"]
    obs_rows += [[f"Claim — {r['title']}", r["reason"], r["severity"]] for r in claims]
    if len(obs_rows) > 1:
        story.append(_table(obs_rows, [40 * mm, 108 * mm, 24 * mm], st))
    story.append(
        Paragraph(
            "Packaging differences are observations for review, not proof of counterfeiting.",
            st["small"],
        )
    )
    h(9)
    story.append(
        _table(
            [["Field", "AI value", "AI confidence"]]
            + [
                [
                    f.label,
                    (fields.get(f.key) or {}).get("ai_value"),
                    f"{(fields.get(f.key) or {}).get('confidence_level', '—')} ({(fields.get(f.key) or {}).get('ai_confidence', 0):.2f})",
                ]
                for f in FIELDS
                if fields.get(f.key)
            ],
            [48 * mm, 92 * mm, 32 * mm],
            st,
        )
    )
    ext = insp.get("extraction") or {}
    story.append(
        Paragraph(
            _t(
                f"Read by: {ext.get('provider') or '—'}{' (OCR fallback)' if ext.get('ocr_used') else ''}. "
                "AI confidence describes legibility; it is not measured accuracy."
            ),
            st["small"],
        )
    )
    h(10)
    corr = [
        [f.label, (fields.get(f.key) or {}).get("ai_value"), (fields.get(f.key) or {}).get("value")]
        for f in FIELDS
        if (fields.get(f.key) or {}).get("status") == "edited"
    ]
    if corr:
        story.append(
            _table(
                [["Field", "Original AI value", "Inspector correction"], *corr],
                [44 * mm, 64 * mm, 64 * mm],
                st,
            )
        )
    dec_rows = [
        [
            f["title"],
            f["decision"]["action"],
            f["decision"].get("corrected_value") or "",
            f["decision"].get("note") or "",
        ]
        for f in insp.get("findings", [])
        if f.get("decision")
    ]
    if dec_rows:
        story.append(Spacer(1, 4))
        story.append(
            _table(
                [["Finding", "Inspector decision", "Correction", "Comment"], *dec_rows],
                [50 * mm, 30 * mm, 46 * mm, 46 * mm],
                st,
            )
        )
    if not corr and not dec_rows:
        story.append(Paragraph("No corrections recorded.", st["p"]))
    h(11)
    sug = insp.get("suggestion") or {}
    story.append(
        _kv(
            [
                (
                    "Final classification (inspector)",
                    CLASS_LABEL.get(decision.get("classification", ""), "—"),
                ),
                ("Suggested (provisional)", CLASS_LABEL.get(sug.get("classification", ""), "—")),
                ("Remarks", decision.get("remarks")),
                (
                    "Typed signature",
                    f"{signature_name} (typed name — not a certified digital signature)",
                ),
                ("Signed at", generated_at.strftime("%d %b %Y, %H:%M UTC")),
            ],
            st,
        )
    )
    h(12)
    for line in [
        "Reference records, licence records and compliance rules are fictional demonstration data maintained by administrators.",
        "A demo licence match is not government verification. A product missing from the reference database is not automatically fake.",
        "Packaging differences are observations, not proof of counterfeiting. Compliance rules are demo rules derived from published "
        "regulations; rule references must be verified against official FSSAI publications.",
        "AI confidence is not measured accuracy. The final classification was selected by the inspector.",
        "Applied rules: "
        + ", ".join(
            f"{r['code']} v{r['version']}"
            for r in (analysis.get("compliance") or {}).get("rules_applied", [])
        ),
        "Official sources: FSSAI (https://www.fssai.gov.in), FoSCoS (https://foscos.fssai.gov.in).",
    ]:
        story.append(Paragraph(_t(line), st["p"]))
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue(), pages["n"]
