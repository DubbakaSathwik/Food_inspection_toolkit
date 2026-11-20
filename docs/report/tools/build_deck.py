"""Builds the CRATE-SCAN presentation (PPTX, then PDF via LibreOffice).  python3 build_deck.py"""

from __future__ import annotations

import pathlib
import re
import subprocess

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

import report_content as C

HERE = pathlib.Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
OUT = HERE.parent
NAME = "CRATE-SCAN_Presentation"

PAGE, SURF, BORDER = RGBColor(0xF6, 0xF2, 0xE6), RGBColor(0xFF, 0xFF, 0xFF), RGBColor(0xD8, 0xD6, 0xC9)
GREEN, GREEN_D, SOFT, TINT, SAGE = (RGBColor(0x56, 0x70, 0x3A), RGBColor(0x3E, 0x52, 0x28), RGBColor(0xE3, 0xEA, 0xCF), RGBColor(0xEE, 0xF2, 0xE1), RGBColor(0xC5, 0xD8, 0x9D))
TEXT, TEXT2 = RGBColor(0x20, 0x23, 0x1D), RGBColor(0x55, 0x58, 0x4E)
WARN_BG, WARN_FG, INFO_BG, INFO_FG = RGBColor(0xFB, 0xEF, 0xD9), RGBColor(0x7A, 0x48, 0x08), RGBColor(0xE2, 0xE8, 0xEE), RGBColor(0x2F, 0x4A, 0x63)
HEAD, BODY = "Cambria", "Calibri"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
slide_no = 0


def rgb_hex(c: RGBColor) -> str:
    return str(c)


def bg(slide, color=PAGE):
    f = slide.background.fill
    f.solid()
    f.fore_color.rgb = color


def rect(slide, x, y, w, h, fill=SURF, line=BORDER, radius=0.06, lw=1.0, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = radius
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(lw)
    s.shadow.inherit = False
    s.text_frame.text = ""
    return s


def _run(p, text, size, color, bold, font, italic=False, highlight=False):
    r = p.add_run()
    r.text = text
    r.font.size, r.font.bold, r.font.italic, r.font.name = Pt(size), bold, italic, font
    r.font.color.rgb = color
    if highlight:
        rpr = r._r.get_or_add_rPr()
        h = etree.SubElement(rpr, qn("a:highlight"))
        c = etree.SubElement(h, qn("a:srgbClr"))
        c.set("val", "FFFF00")
        # a:highlight must come after a:solidFill in schema order
        sf = rpr.find(qn("a:solidFill"))
        if sf is not None:
            rpr.remove(h)
            sf.addnext(h)


def rich(p, text, size, color, bold=False, font=BODY, italic=False):
    for part in re.split(r"(\*\*.+?\*\*|\[\[.+?\]\])", text):
        if not part:
            continue
        if part.startswith("**"):
            _run(p, part[2:-2], size, color, True, font, italic)
        elif part.startswith("[["):
            _run(p, "[" + part[2:-2] + "]", size, TEXT, bold, font, italic, highlight=True)
        else:
            _run(p, part, size, color, bold, font, italic)


def bullet_ppr(p, indent_in=0.22, char="•", color: RGBColor | None = None):
    ppr = p._p.get_or_add_pPr()
    ppr.set("marL", str(int(Inches(indent_in))))
    ppr.set("indent", str(-int(Inches(indent_in))))
    for tag in ("a:buNone", "a:buChar", "a:buClr"):
        for e in ppr.findall(qn(tag)):
            ppr.remove(e)
    if color is not None:
        bc = etree.SubElement(ppr, qn("a:buClr"))
        c = etree.SubElement(bc, qn("a:srgbClr"))
        c.set("val", rgb_hex(color))
    bu = etree.SubElement(ppr, qn("a:buChar"))
    bu.set("char", char)


def text(slide, x, y, w, h, paras, size=16, color=TEXT, bold=False, font=BODY, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, bullets=False,
         space_after=6, line=1.08, italic=False):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.04)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    if isinstance(paras, str):
        paras = [paras]
    for i, t in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after)
        p.line_spacing = line
        if bullets:
            bullet_ppr(p, color=GREEN)
        rich(p, t, size, color, bold, font, italic)
    return tb


def chip(slide, x, y, w, label, fill=SOFT, fg=GREEN_D, size=11, h=0.3):
    s = rect(slide, x, y, w, h, fill, None, radius=0.5)
    tf = s.text_frame
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    _run(p, label, size, fg, True, BODY)


def picture(slide, path, x, y, w=None, h=None, frame=True, rounded=True):
    kw = {}
    if w:
        kw["width"] = Inches(w)
    if h:
        kw["height"] = Inches(h)
    pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y), **kw)
    if rounded:
        try:
            pic.auto_shape_type = MSO_SHAPE.ROUNDED_RECTANGLE
            pic.adjustments[0] = 0.025 if hasattr(pic, "adjustments") else None
        except Exception:
            pass
    if frame:
        pic.line.color.rgb = BORDER
        pic.line.width = Pt(1.25)
    return pic


def new_slide(title=None, kicker=None):
    global slide_no
    slide_no += 1
    s = prs.slides.add_slide(BLANK)
    bg(s)
    if title:
        rect(s, 0, 0, 0.18, 7.5, GREEN, None, shape=MSO_SHAPE.RECTANGLE)
        if kicker:
            chip(s, 0.6, 0.38, 0.35 + 0.095 * len(kicker), kicker.upper(), SOFT, GREEN_D, 10.5)
        text(s, 0.55, 0.72, 12.2, 0.8, title, 32, GREEN_D, True, HEAD, anchor=MSO_ANCHOR.MIDDLE)
        ln = s.shapes.add_connector(1, Inches(0.6), Inches(1.52), Inches(1.9), Inches(1.52))
        ln.line.color.rgb = GREEN
        ln.line.width = Pt(3)
        text(s, 0.6, 7.08, 8, 0.3, "CRATE-SCAN · MVSR Engineering College · Department of CSE", 10, TEXT2)
        text(s, 12.0, 7.08, 0.8, 0.3, str(slide_no), 10, TEXT2, align=PP_ALIGN.RIGHT)
    return s


def card(slide, x, y, w, h, title=None, body=None, size=14, fill=SURF, line=BORDER, tcolor=GREEN_D, tsize=16, bullets=False, bcolor=TEXT2):
    rect(slide, x, y, w, h, fill, line)
    cy = y + 0.14
    if title:
        text(slide, x + 0.2, cy, w - 0.4, 0.4, title, tsize, tcolor, True, BODY)
        cy += 0.42
    if body:
        text(slide, x + 0.2, cy, w - 0.4, h - (cy - y) - 0.1, body, size, bcolor, bullets=bullets, space_after=4)


def deck_diagram(name):
    """Diagram PNG without its own title band (the slide has a title)."""
    from PIL import Image

    out = ASSETS / "diagrams" / "deck"
    out.mkdir(exist_ok=True)
    dst = out / f"{name}.png"
    im = Image.open(ASSETS / "diagrams" / f"{name}.png")
    im.crop((0, 135, im.size[0], im.size[1])).save(dst)
    return dst


def img(name, kind="diagrams", mob=False):
    if kind == "screens":
        return ASSETS / "screens" / ("mobile" if mob else "desktop") / f"{name}.png"
    return ASSETS / kind / f"{name}.png"


# ---------------------------------------------------------------- slides
def title_slide():
    global slide_no
    slide_no += 1
    s = prs.slides.add_slide(BLANK)
    bg(s, SURF)
    picture(s, ASSETS / "brand" / "college_banner.jpg", 1.87, 0.12, w=9.6, frame=False, rounded=False)
    rect(s, 0.6, 2.5, 6.3, 4.45, TINT, None, radius=0.04)
    text(s, 0.9, 2.65, 5.8, 0.4, "MINI PROJECT", 14, GREEN, True, BODY)
    text(s, 0.9, 3.0, 5.9, 1.0, "CRATE-SCAN", 48, GREEN_D, True, HEAD)
    text(s, 0.9, 4.0, 5.8, 1.0, "AI-Assisted Food Product Inspection Toolkit", 24, TEXT, False, HEAD)
    text(s, 0.9, 5.0, 5.8, 0.7, "Photograph · Read · Verify · Analyse · Decide · Report", 14, TEXT2, italic=True)
    names = "   ".join(f"{n}, {r}" for n, r in C.TEAM)
    text(s, 0.9, 5.6, 5.9, 1.2, ["**Team:** " + " | ".join(f"{n} ({r})" for n, r in C.TEAM), f"**Guide:** {C.GUIDE[0]}, {C.GUIDE[1]}"], 12.5, TEXT, space_after=4)
    _ = names
    picture(s, img("07-findings", "screens"), 7.2, 2.5, w=5.5, frame=True)
    picture(s, img("07-findings", "screens", mob=True), 11.3, 4.35, w=1.5, frame=True)
    chip(s, 7.2, 5.75, 2.5, "Next.js · FastAPI · MongoDB", SOFT, GREEN_D, 11)
    return s


def problem_slide():
    s = new_slide("Problem Statement, Scope and Objectives", "Introduction")
    rect(s, 0.6, 1.85, 12.1, 1.55, GREEN_D, None, radius=0.05)
    text(s, 0.9, 1.95, 11.5, 1.4,
         "Inspectors must read many mandatory label declarations, check formats, and compare them with licence records and regulations — slowly, inconsistently, and with poorly documented evidence. "
         "AI can read labels fast, but it cannot be the final authority: **a safe tool keeps the inspector in control.**", 17, RGBColor(0xFF, 0xFF, 0xFF), anchor=MSO_ANCHOR.MIDDLE, line=1.1)
    card(s, 0.6, 3.65, 5.9, 3.25, "Project scope", [
        "A guided web workflow for inspectors, on phone or desktop", "AI reading of 22 label fields with confidence per field",
        "Matching against reference records and configurable rules", "13-section PDF report; admin console, analytics and audit log",
        "Role-based, privacy-conscious and security-tested"], 16, bullets=True)
    card(s, 6.8, 3.65, 5.9, 3.25, "Objectives", [
        "Cut the time to inspect and document a product", "Make AI suggestions transparent: value, confidence, correction",
        "Keep every decision with the inspector; record who decided what", "Protect photographs: originals deleted after the report",
        "Keep working when an AI provider is slow or down"], 16, bullets=True)


def applications_slide():
    s = new_slide("Application Areas and Challenges", "Introduction")
    card(s, 0.6, 1.85, 5.9, 5.05, "Application areas", [a for a, _ in C.APPLICATIONS], 18, bullets=True)
    card(s, 6.8, 1.85, 5.9, 5.05, "Challenges addressed", [
        "AI can misread small print → confidence + human verification", "Providers can be slow or unavailable → retry, fallback, incomplete state",
        "Photographs are sensitive → owner-only access, delete after report", "Role misuse → admin approval and server-side role checks",
        "Phones in the field → mobile-first layout, autosave", "Trust in findings → rules, evidence photos, audit trail"], 17, bullets=True)


def tech_slide():
    s = new_slide("Technology Stack", "Requirements")
    items = [("Next.js 16 · React 19", "TypeScript, Tailwind CSS 4 — responsive UI"), ("FastAPI · Python 3.12", "Pydantic v2 typed API, 78 routes"),
             ("MongoDB Atlas", "Documents + GridFS files, validators, migrations"), ("Firebase Auth", "Google sign-in, ID tokens, role claims"),
             ("Gemini · NVIDIA · OCR", "Ordered AI fallback for label reading"), ("ReportLab · Pillow", "13-section PDF, photo checks and compression"),
             ("Render", "API and website, auto-deploy after checks"), ("GitHub Actions", "Tests, security scans, CodeQL, build")]
    for i, (a, b) in enumerate(items):
        x, y = 0.6 + (i % 4) * 3.07, 1.9 + (i // 4) * 2.1
        rect(s, x, y, 2.9, 1.9, SOFT if (i + i // 4) % 2 == 0 else SURF, GREEN if (i + i // 4) % 2 == 0 else BORDER)
        text(s, x + 0.18, y + 0.2, 2.55, 0.8, a, 17, GREEN_D, True, HEAD)
        text(s, x + 0.18, y + 1.0, 2.55, 0.85, b, 12.5, TEXT2)
    text(s, 0.6, 6.25, 12.1, 0.6, "Developer tools: Visual Studio Code · Git/GitHub · uv · pnpm · Docker · Playwright · pytest · Vitest", 13, TEXT2, italic=True)
    text(s, 0.6, 6.6, 12.1, 0.4, "Hardware: laptop (Core i3+, 8 GB RAM) · phone with camera · Render free instances (512 MB) · Atlas free cluster", 13, TEXT2, italic=True)


def io_slide():
    s = new_slide("Input and Output Specifications", "Requirements")
    card(s, 0.6, 1.85, 5.9, 5.05, "Inputs", [
        "**Photographs:** JPG, PNG, WebP — up to 5, up to 12 MB, 50 MP cap", "**Sign-in:** Google account (verified by Firebase)",
        "**Inspector actions:** confirm/correct 22 label fields, decide findings, final classification, notes",
        "**Admin data:** reference records (manual, CSV import, AI-assisted draft), compliance rules, settings",
        "**Questions** to the Ask-AI assistant"], 16, bullets=True)
    card(s, 6.8, 1.85, 5.9, 5.05, "Outputs", [
        "**Structured readings:** 22 fields with confidence and flags", "**Findings:** rule, expected vs found, severity, evidence photo",
        "**PDF report:** 13 sections, decision and disclaimers; CSV/Excel exports",
        "**Dashboards:** inspector history; admin analytics, audit log, diagnostics", "**Assistant answers** with sources when web research is on"], 16, bullets=True)


def diagram_slide(title, kicker, name, caption=None, w=11.2):
    s = new_slide(title, kicker)
    from PIL import Image

    path = deck_diagram(name)
    im = Image.open(path)
    ratio = im.size[1] / im.size[0]
    max_h = 5.15 if not caption else 4.75
    wi = min(w, max_h / ratio)
    x = (13.333 - wi) / 2
    picture(s, path, x, 1.8, w=wi, frame=True)
    if caption:
        text(s, 0.6, 6.55, 12.1, 0.45, caption, 13.5, TEXT2, italic=True, align=PP_ALIGN.CENTER)
    return s


def modules_slide():
    s = new_slide("Module Description", "Design")
    mods = C.MODULES
    half = (len(mods) + 1) // 2
    for col, group in enumerate((mods[:half], mods[half:])):
        for i, (a, b) in enumerate(group):
            x, y = 0.6 + col * 6.15, 1.8 + i * 0.74
            rect(s, x, y, 5.95, 0.68, SURF, BORDER, radius=0.12)
            text(s, x + 0.14, y + 0.03, 1.85, 0.62, a, 11.5, GREEN_D, True, anchor=MSO_ANCHOR.MIDDLE)
            text(s, x + 2.0, y + 0.03, 3.9, 0.62, b, 9.5, TEXT2, anchor=MSO_ANCHOR.MIDDLE, line=1.0, space_after=0)


def security_slide():
    s = new_slide("Security by Design", "Design")
    from PIL import Image

    path = deck_diagram("security_layers")
    im = Image.open(path)
    wi = 7.9
    picture(s, path, 0.6, 1.85, w=wi)
    card(s, 8.8, 1.85, 3.9, 4.95, "Why it holds up", [
        "Roles from server records, not the browser", "Other users' data answers “not found”", "Unknown fields and operators rejected",
        "Rate limits use the real client address", "Secrets only in the host; repo scanned", "Admin actions audited, append-only"], 13, bullets=True)
    _ = im


def code_slide():
    s = new_slide("Implementation Highlights", "Implementation")
    code = ["def _own(p, inspection_id):", "    return {\"_id\": inspection_id,", "            \"owner_uid\": p.uid}", "",
            "async def get(p, inspection_id):", "    doc = await col(\"inspections\").find_one(", "        _own(p, inspection_id))", "    if not doc:", "        raise not_found(\"Inspection\")", "    return doc"]
    rect(s, 0.6, 1.85, 6.6, 3.15, RGBColor(0x1F, 0x24, 0x1B), None, radius=0.04)
    text(s, 0.85, 1.95, 6.2, 0.35, "Owner-scoped data access (simplified excerpt)", 12, SAGE, True)
    text(s, 0.85, 2.35, 6.2, 2.6, code, 12, RGBColor(0xEE, 0xF2, 0xE1), font="Consolas", space_after=1, line=1.0)
    card(s, 0.6, 5.2, 6.6, 1.7, "Layered back-end", [
        "Routers → services → repositories; only repositories touch MongoDB", "An architecture test fails the build if a router breaks the rule"], 13, bullets=True)
    stats = [("78", "API routes"), ("22", "label fields"), ("13", "PDF sections"), ("~9k", "lines of Python"), ("~15k", "lines of TypeScript"), ("8", "issues found and fixed")]
    for i, (n, l) in enumerate(stats):
        x, y = 7.5 + (i % 2) * 2.65, 1.85 + (i // 2) * 1.7
        rect(s, x, y, 2.5, 1.55, SOFT if i % 3 == 0 else SURF, GREEN if i % 3 == 0 else BORDER)
        text(s, x, y + 0.18, 2.5, 0.8, n, 36, GREEN_D, True, HEAD, align=PP_ALIGN.CENTER)
        text(s, x, y + 1.0, 2.5, 0.4, l, 13, TEXT2, align=PP_ALIGN.CENTER)


def results_slide(title, pairs, kicker="Testing / Results"):
    s = new_slide(title, kicker)
    n = len(pairs)
    if n == 2:
        w = 5.95
        for i, (name, cap, mob) in enumerate(pairs):
            x = 0.6 + i * 6.15
            picture(s, img(name, "screens"), x, 1.85, w=w)
            text(s, x, 1.85 + w / 1.6 + 0.1, w, 0.4, cap, 14, GREEN_D, True, align=PP_ALIGN.CENTER)
    else:
        w = 3.95
        for i, (name, cap, mob) in enumerate(pairs):
            x = 0.6 + i * 4.08
            picture(s, img(name, "screens"), x, 1.95, w=w)
            text(s, x, 1.95 + w / 1.6 + 0.1, w, 0.4, cap, 13, GREEN_D, True, align=PP_ALIGN.CENTER)
    return s


def mobile_slide():
    s = new_slide("Testing / Results: Mobile Layout", "Testing / Results")
    names = [("03-inspector-dashboard", "Inspector dashboard"), ("04-new-inspection", "New inspection"), ("07-findings", "Findings"), ("11-admin-dashboard", "Admin dashboard"), ("18-diagnostics", "Diagnostics")]
    from PIL import Image

    for i, (nm, cap) in enumerate(names):
        im = Image.open(img(nm, "screens", mob=True))
        h = 4.45
        w = h * im.size[0] / im.size[1]
        x = 0.7 + i * 2.45
        picture(s, img(nm, "screens", mob=True), x, 1.85, h=h)
        text(s, x - 0.2, 6.4, 2.2, 0.4, cap, 12.5, GREEN_D, True, align=PP_ALIGN.CENTER)
    text(s, 0.6, 6.78, 12.1, 0.3, "iPhone 14 viewport (390 px): bottom tab bar, no horizontal scrolling, verified by automated browser tests", 11.5, TEXT2, italic=True, align=PP_ALIGN.CENTER)


def testing_slide():
    s = new_slide("Testing Summary", "Testing / Results")
    tiles = [("75", "backend tests", "89 % coverage"), ("9", "unit tests", "front-end"), ("44", "browser tests", "desktop + mobile"), ("49", "attack tests", "security suite"), ("6", "required CI checks", "all green")]
    for i, (n, a, b) in enumerate(tiles):
        x = 0.6 + i * 2.45
        rect(s, x, 1.85, 2.3, 2.05, SOFT if i % 2 == 0 else SURF, GREEN if i % 2 == 0 else BORDER)
        text(s, x, 1.95, 2.3, 0.9, n, 44, GREEN_D, True, HEAD, align=PP_ALIGN.CENTER)
        text(s, x, 2.85, 2.3, 0.4, a, 14.5, TEXT, True, align=PP_ALIGN.CENTER)
        text(s, x, 3.25, 2.3, 0.4, b, 12.5, TEXT2, align=PP_ALIGN.CENTER)
    card(s, 0.6, 4.15, 6.0, 2.75, "What the attacks covered", [
        "Forged, expired and replayed tokens (74 operations)", "Cross-user access, role escalation, NoSQL injection",
        "Malicious uploads and pixel bombs; parallel AI-quota races", "Rate-limit spoofing, CORS, headers, production mode"], 13, bullets=True)
    card(s, 6.8, 4.15, 5.9, 2.75, "Issues found and fixed", [
        "Huge-image memory exhaustion → 50 MP cap", "X-Forwarded-For rate-limit bypass → trusted proxy chain",
        "Reasoning-model empty answers → thinking switched off", "Flaky upload test → wait for React hydration"], 13, bullets=True)


def cicd_slide():
    diagram_slide("CI/CD and Deployment", "Deployment", "cicd", "Protected main branch · six required checks · Render deploys API and website after checks pass", w=11.0)


def conclusion_slide():
    s = new_slide("Conclusion and Future Enhancements", "Conclusion")
    card(s, 0.6, 1.85, 5.9, 5.05, "Conclusion", [
        "Delivers a guided, evidence-based inspection tool that keeps the inspector in charge", "Layered, secure architecture with owner-scoped data and role-based access",
        "Verified at five levels: unit, API, browser, attack-style and static scans", "Limitations: demo reference data, provider availability, free-tier sleep"], 16, bullets=True)
    card(s, 6.8, 1.85, 5.9, 5.05, "Future enhancements", [f"**{a}:** {b.split('.')[0]}" for a, b in C.FUTURE[:5]], 14.5, bullets=True)


def references_slide():
    s = new_slide("References", "References")
    left, right = C.BIBLIOGRAPHY[:7], C.BIBLIOGRAPHY[7:]
    for col, grp in enumerate((left, right)):
        paras = []
        for i, (a, u) in enumerate(grp):
            paras.append(f"**{a}**")
            paras.append(u)
        tb = text(s, 0.6 + col * 6.2, 1.85, 6.0, 5.0, paras, 12.5, TEXT, space_after=2)
        for j, p in enumerate(tb.text_frame.paragraphs):
            if j % 2 == 1:
                for r in p.runs:
                    r.font.color.rgb = RGBColor(0x1F, 0x4E, 0x9E)
                    r.font.size = Pt(11.5)
                p.space_after = Pt(9)


def thanks_slide():
    global slide_no
    slide_no += 1
    s = prs.slides.add_slide(BLANK)
    bg(s, SURF)
    picture(s, ASSETS / "brand" / "college_banner.jpg", 1.87, 0.12, w=9.6, frame=False, rounded=False)
    rect(s, 0.6, 2.5, 12.1, 4.3, TINT, None, radius=0.04)
    text(s, 0.6, 2.75, 12.1, 1.0, "Thank You!", 50, GREEN_D, True, HEAD, align=PP_ALIGN.CENTER)
    for i, (lab, fill) in enumerate((("Questions?", SOFT), ("Comments?", SURF), ("Suggestions?", SOFT))):
        rect(s, 2.9 + i * 2.6, 3.95, 2.4, 0.75, fill, GREEN, radius=0.5)
        text(s, 2.9 + i * 2.6, 3.95, 2.4, 0.75, lab, 17, GREEN_D, True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 0.9, 5.1, 11.5, 1.5, ["**CRATE-SCAN** – AI-Assisted Food Product Inspection Toolkit", "**Team:** " + " | ".join(f"{n} ({r})" for n, r in C.TEAM), f"**Guide:** {C.GUIDE[0]}, {C.GUIDE[1]}"],
         14.5, TEXT, align=PP_ALIGN.CENTER, space_after=4)


def tech_io_slide():
    s = new_slide("Technology Stack and Input / Output", "Requirements")
    items = [("Next.js 16 · React 19", "TypeScript, Tailwind — responsive UI"), ("FastAPI · Python 3.12", "Typed API, 78 routes"), ("MongoDB Atlas", "Documents + GridFS files"), ("Firebase Auth", "Google sign-in, role claims"),
             ("Gemini · NVIDIA · OCR", "Ordered AI fallback"), ("ReportLab · Pillow", "13-section PDF, photo checks"), ("Render", "API + website auto-deploy"), ("GitHub Actions", "Tests, scans, CodeQL")]
    for i, (a, b) in enumerate(items):
        x, y = 0.6 + (i % 4) * 3.07, 1.85 + (i // 4) * 1.45
        rect(s, x, y, 2.9, 1.3, SOFT if (i + i // 4) % 2 == 0 else SURF, GREEN if (i + i // 4) % 2 == 0 else BORDER)
        text(s, x + 0.15, y + 0.12, 2.6, 0.5, a, 15.5, GREEN_D, True, HEAD)
        text(s, x + 0.15, y + 0.72, 2.6, 0.5, b, 12, TEXT2)
    card(s, 0.6, 4.85, 5.95, 2.05, "Inputs", ["Up to 5 product photos (JPG, PNG, WebP)", "Google sign-in; inspector confirmations, corrections and decisions", "Admin data: reference records, rules, settings"], 14.5, bullets=True)
    card(s, 6.75, 4.85, 5.95, 2.05, "Outputs", ["22 label fields with confidence; findings with evidence", "13-section PDF report; CSV / Excel exports", "Dashboards: history, analytics, audit log, diagnostics"], 14.5, bullets=True)


def workflow_actors_slide():
    s = new_slide("Inspection Workflow and Users", "Design")
    from PIL import Image

    path = deck_diagram("workflow")
    im = Image.open(path)
    wi = min(10.3, 4.1 / (im.size[1] / im.size[0]))
    picture(s, path, (13.333 - wi) / 2, 1.75, w=wi)
    roles = [("Inspector", "Photographs, verifies fields, decides findings, downloads the report, asks AI"),
             ("Admin", "Approves users, manages reference data and rules, reviews proposals, analytics, diagnostics"),
             ("Super Admin", "Everything an admin does, plus managing administrator accounts")]
    for i, (a, b) in enumerate(roles):
        x = 0.6 + i * 4.1
        rect(s, x, 6.0, 3.95, 0.95, SOFT if i == 0 else (INFO_BG if i == 1 else WARN_BG), None, radius=0.1)
        text(s, x + 0.15, 6.03, 3.65, 0.3, a, 13, GREEN_D if i == 0 else (INFO_FG if i == 1 else WARN_FG), True)
        text(s, x + 0.15, 6.32, 3.65, 0.62, b, 10.5, TEXT2, line=1.0, space_after=0)


def modules_data_slide():
    s = new_slide("Modules and Data Model", "Design")
    mods = [("User and access", "Google sign-in, approval, roles, invitations"), ("Inspection workflow", "Six guided, auto-saved steps"),
            ("AI extraction and validation", "Provider chain, retry, OCR fallback, format checks"), ("Matching and rules", "Reference matching, versioned compliance rules"),
            ("Report generator", "13-section PDF with evidence and disclaimers"), ("Ask-AI and proposals", "Assistant with history; new-product proposals"),
            ("Admin, analytics and audit", "Users, reference data, charts, append-only audit log"), ("Diagnostics and security", "Live dependency checks; rate limits, roles, owner-scoped data")]
    for i, (a, b) in enumerate(mods):
        x, y = 0.6 + (i % 2) * 4.15, 1.8 + (i // 2) * 1.2
        rect(s, x, y, 4.0, 1.08, SURF, BORDER, radius=0.1)
        text(s, x + 0.15, y + 0.08, 3.7, 0.35, a, 13.5, GREEN_D, True)
        text(s, x + 0.15, y + 0.46, 3.7, 0.6, b, 11.5, TEXT2, line=1.0, space_after=0)
    card(s, 9.1, 1.8, 3.6, 4.7, "MongoDB collections", [
        "users · user_invites", "inspections (22 fields, findings, decision)", "inspection_notes", "reference_records (demo data)", "compliance_rules (versioned)", "product_proposals",
        "chat_messages · audit_logs", "usage_metrics · counters · settings", "GridFS: photos, reports, images"], 11.5, bullets=True)
    text(s, 0.6, 6.7, 8.4, 0.35, "Validators and indexes are created by ordered, idempotent migrations.", 11.5, TEXT2, italic=True)


def ui_slide():
    s = new_slide("Results: User Interface", "Testing / Results")
    shots = [("05-verify-fields", "Verify extracted fields"), ("07-findings", "Findings and evidence"), ("08-report", "Inspection report"), ("11-admin-dashboard", "Admin dashboard")]
    for i, (nm, cap) in enumerate(shots):
        x, y = 0.6 + (i % 2) * 3.95, 1.8 + (i // 2) * 2.6
        picture(s, img(nm, "screens"), x, y, w=3.7)
        text(s, x, y + 2.33, 3.7, 0.3, cap, 11.5, GREEN_D, True, align=PP_ALIGN.CENTER)
    card(s, 8.7, 1.8, 4.0, 4.95, "What the tests confirm", [
        "Every screen renders on desktop and phone", "No console errors or sideways scrolling", "AI value kept beside the inspector's correction",
        "Findings show rule, evidence and decision", "Report preview and PDF download"], 14, bullets=True)


def security_testing_slide():
    s = new_slide("Security and Testing", "Testing / Results")
    tiles = [("75", "backend tests", "89 % coverage"), ("9", "unit tests", "front-end"), ("44", "browser tests", "desktop + mobile"), ("49", "attack tests", "security suite"), ("6", "CI checks", "all green")]
    for i, (n, a, b) in enumerate(tiles):
        x = 0.6 + i * 2.45
        rect(s, x, 1.8, 2.3, 1.75, SOFT if i % 2 == 0 else SURF, GREEN if i % 2 == 0 else BORDER)
        text(s, x, 1.85, 2.3, 0.8, n, 38, GREEN_D, True, HEAD, align=PP_ALIGN.CENTER)
        text(s, x, 2.62, 2.3, 0.4, a, 13.5, TEXT, True, align=PP_ALIGN.CENTER)
        text(s, x, 2.98, 2.3, 0.4, b, 11.5, TEXT2, align=PP_ALIGN.CENTER)
    card(s, 0.6, 3.8, 6.0, 3.1, "Security by design", [
        "Google-only sign-in; admin approval; server-side roles", "Every request: rate limit → token check → role → owner-scoped query", "Strict models; uploads decoded and size/pixel limited",
        "Originals deleted after the report; audit log append-only", "Protected main branch; secrets scanned"], 14, bullets=True)
    card(s, 6.8, 3.8, 5.9, 3.1, "Attacks tested, issues fixed", [
        "Forged tokens, cross-user access, injection, bad uploads", "Huge-image memory exhaustion → 50 MP cap", "Rate-limit spoofing → trusted proxy chain",
        "Reasoning-model empty answers → thinking off", "Flaky tests and CSP gaps → fixed in CI"], 14, bullets=True)


def closing_slide():
    global slide_no
    slide_no += 1
    s = prs.slides.add_slide(BLANK)
    bg(s)
    rect(s, 0, 0, 0.18, 7.5, GREEN, None, shape=MSO_SHAPE.RECTANGLE)
    chip(s, 0.6, 0.38, 2.2, "CONCLUSION", SOFT, GREEN_D, 10.5)
    text(s, 0.55, 0.72, 12.2, 0.8, "Conclusion, Future Work and References", 32, GREEN_D, True, HEAD, anchor=MSO_ANCHOR.MIDDLE)
    card(s, 0.6, 1.75, 4.0, 3.95, "Conclusion", ["Guided, evidence-based inspection with the inspector in charge", "Layered, secure and tested at five levels", "Limits: demo reference data, AI availability, free-tier sleep"], 14, bullets=True)
    card(s, 4.75, 1.75, 4.0, 3.95, "Future enhancements", ["Official reference data and licence verification", "Mobile app with offline mode and barcode scan", "Multilingual labels; model evaluation", "Assignment, supervisor review, trend alerts"], 14, bullets=True)
    refs = ["FastAPI · fastapi.tiangolo.com", "Next.js · nextjs.org/docs", "MongoDB · mongodb.com/docs", "Firebase Auth · firebase.google.com/docs/auth", "Gemini API · ai.google.dev/gemini-api/docs", "FSSAI · fssai.gov.in", "OWASP ASVS · owasp.org"]
    card(s, 8.9, 1.75, 3.8, 3.95, "References", refs, 12.5, bullets=True)
    rect(s, 0.6, 5.95, 12.1, 0.95, GREEN_D, None, radius=0.12)
    text(s, 0.9, 5.98, 5, 0.9, "Thank You!  Questions?", 26, RGBColor(0xFF, 0xFF, 0xFF), True, HEAD, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 6.2, 5.98, 6.3, 0.9, ["**Team:** " + " | ".join(f"{n} ({r})" for n, r in C.TEAM), f"**Guide:** {C.GUIDE[0]}, {C.GUIDE[1]}"], 11.5, RGBColor(0xFF, 0xFF, 0xFF), anchor=MSO_ANCHOR.MIDDLE, space_after=2)


def build():
    title_slide()
    problem_slide()
    applications_slide()
    tech_io_slide()
    diagram_slide("Proposed System Architecture", "Design", "architecture")
    workflow_actors_slide()
    modules_data_slide()
    ui_slide()
    security_testing_slide()
    closing_slide()
    out = OUT / f"{NAME}.pptx"
    prs.save(out)
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(OUT), str(out)], check=True, capture_output=True, timeout=300)
    print("written", out, "and PDF; slides:", len(prs.slides))


if __name__ == "__main__":
    build()
