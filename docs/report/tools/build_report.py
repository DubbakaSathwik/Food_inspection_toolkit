"""Builds the CRATE-SCAN project report (DOCX, then PDF via LibreOffice).

  python3 build_report.py            # writes ../CRATE-SCAN_Project_Report.docx and .pdf

Two passes: the first conversion finds the page of every heading/figure, the second fills the table of contents."""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

import report_content as C

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ASSETS = HERE.parent / "assets"
OUTDIR = HERE.parent
NAME = "CRATE-SCAN_Project_Report"
FONT = "Times New Roman"
GREEN = RGBColor(0x3E, 0x52, 0x28)


# ------------------------------------------------------------------ low-level helpers
def set_font(run, size=None, bold=None, italic=None, name=FONT, color=None):
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(a), name)
    if size:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color


def add_runs(p, text, size=12, bold=False, italic=False, name=FONT):
    """Mini markup: **bold** and [[placeholder]] (yellow highlight); placeholders may sit inside bold text."""

    def emit(chunk, is_bold):
        for part in re.split(r"(\[\[.+?\]\])", chunk):
            if not part:
                continue
            if part.startswith("[["):
                r = p.add_run("[" + part[2:-2] + "]")
                set_font(r, size, bold or is_bold, italic, name)
                r.font.highlight_color = WD_COLOR_INDEX.YELLOW
            else:
                r = p.add_run(part)
                set_font(r, size, bold or is_bold, italic, name)

    for part in re.split(r"(\*\*.+?\*\*)", text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            emit(part[2:-2], True)
        else:
            emit(part, False)


def shade(cell, hex_fill):
    tcpr = cell._element.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcpr.append(shd)


def cell_margins(cell, top=60, bottom=60, left=100, right=100):
    tcpr = cell._element.get_or_add_tcPr()
    mar = OxmlElement("w:tcMar")
    for k, v in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        e = OxmlElement(f"w:{k}")
        e.set(qn("w:w"), str(v))
        e.set(qn("w:type"), "dxa")
        mar.append(e)
    tcpr.append(mar)


def field(run, instr):
    for kind, text in (("begin", None), (None, instr), ("end", None)):
        if kind:
            e = OxmlElement("w:fldChar")
            e.set(qn("w:fldCharType"), kind)
        else:
            e = OxmlElement("w:instrText")
            e.set(qn("xml:space"), "preserve")
            e.text = text
        run._element.append(e)


def page_number_footer(section, first_blank=False):
    section.footer.is_linked_to_previous = False
    section.different_first_page_header_footer = first_blank
    p = section.footer.paragraphs[0]
    p.text = ""
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run()
    set_font(r, 11)
    field(r, "PAGE")


def numbering(section, fmt, start):
    sect = section._sectPr
    for e in sect.findall(qn("w:pgNumType")):
        sect.remove(e)
    pg = OxmlElement("w:pgNumType")
    pg.set(qn("w:fmt"), fmt)
    pg.set(qn("w:start"), str(start))
    sect.append(pg)


def para_border_bottom(p, color="56703A", sz=8):
    ppr = p._element.get_or_add_pPr()
    b = OxmlElement("w:pBdr")
    bot = OxmlElement("w:bottom")
    bot.set(qn("w:val"), "single")
    bot.set(qn("w:sz"), str(sz))
    bot.set(qn("w:space"), "1")
    bot.set(qn("w:color"), color)
    b.append(bot)
    ppr.append(b)


# ------------------------------------------------------------------ document builder
class Report:
    def __init__(self, figs, toc_pages):
        self.doc = Document()
        self.figs = figs  # list of captions for the list of figures (from the previous pass)
        self.found_figs: list[str] = []
        self.toc_entries: list[tuple[int, str]] = []
        self.toc_pages = toc_pages
        d = self.doc
        s = d.sections[0]
        s.page_width, s.page_height = Cm(21.0), Cm(29.7)
        s.left_margin, s.right_margin, s.top_margin, s.bottom_margin = Cm(2.8), Cm(2.4), Cm(2.5), Cm(2.3)
        st = d.styles["Normal"]
        st.font.name, st.font.size = FONT, Pt(12)
        st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        for lvl, size in ((1, 16), (2, 14), (3, 12)):
            h = d.styles[f"Heading {lvl}"]
            h.font.name, h.font.size, h.font.bold = FONT, Pt(size), True
            h.font.color.rgb = RGBColor(0, 0, 0)
            h.element.rPr.rFonts.set(qn("w:ascii"), FONT)
            h.element.rPr.rFonts.set(qn("w:hAnsi"), FONT)
            h.paragraph_format.space_before = Pt(14 if lvl > 1 else 0)
            h.paragraph_format.space_after = Pt(8)
            h.paragraph_format.keep_with_next = True

    # ---- generic blocks
    def P(self, text, size=12, align="j", bold=False, italic=False, after=6, before=0, indent=None, keep=False):
        p = self.doc.add_paragraph()
        p.alignment = {"j": WD_ALIGN_PARAGRAPH.JUSTIFY, "c": WD_ALIGN_PARAGRAPH.CENTER, "l": WD_ALIGN_PARAGRAPH.LEFT, "r": WD_ALIGN_PARAGRAPH.RIGHT}[align]
        pf = p.paragraph_format
        pf.space_after, pf.space_before, pf.line_spacing = Pt(after), Pt(before), 1.2
        if indent:
            pf.left_indent = Cm(indent)
        pf.keep_with_next = keep
        add_runs(p, text, size, bold, italic)
        return p

    def H1(self, text, new_page=True):
        h = self.doc.add_heading(text, 1)
        h.paragraph_format.page_break_before = new_page
        self.toc_entries.append((1, text))
        return h

    def H2(self, text):
        self.toc_entries.append((2, text))
        return self.doc.add_heading(text, 2)

    def H3(self, text):
        return self.doc.add_heading(text, 3)

    def bullets(self, items, size=12, indent=0.9, keep=False):
        for it in items:
            p = self.doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            pf = p.paragraph_format
            pf.left_indent, pf.first_line_indent, pf.space_after, pf.line_spacing = Cm(indent + 0.6), Cm(-0.6), Pt(3), 1.15
            pf.keep_with_next = keep
            add_runs(p, "●  " + it, size)

    def titled_bullet(self, title, desc):
        p = self.P(f"●  **{title}**", after=1, keep=True, align="l")
        p.paragraph_format.left_indent = Cm(0.6)
        q = self.P(desc, after=8)
        q.paragraph_format.left_indent = Cm(1.2)

    def numbered(self, items):
        for i, it in enumerate(items, 1):
            p = self.doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            pf = p.paragraph_format
            pf.left_indent, pf.first_line_indent, pf.space_after, pf.line_spacing = Cm(1.2), Cm(-0.7), Pt(4), 1.15
            add_runs(p, f"{i}.  {it}", 12)

    def table(self, headers, rows, widths_cm, size=10.5, header_fill="E3EACF", bold_first=False):
        t = self.doc.add_table(rows=1, cols=len(headers))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        for i, h in enumerate(headers):
            c = t.rows[0].cells[i]
            c.width = Cm(widths_cm[i])
            shade(c, header_fill)
            cell_margins(c)
            c.paragraphs[0].text = ""
            add_runs(c.paragraphs[0], h, size, bold=True)
        trpr = t.rows[0]._tr.get_or_add_trPr()
        th = OxmlElement("w:tblHeader")
        trpr.append(th)
        for row in rows:
            cells = t.add_row().cells
            cant = OxmlElement("w:cantSplit")
            t.rows[-1]._tr.get_or_add_trPr().append(cant)
            for i, val in enumerate(row):
                cells[i].width = Cm(widths_cm[i])
                cell_margins(cells[i])
                cells[i].paragraphs[0].text = ""
                cells[i].paragraphs[0].paragraph_format.space_after = Pt(0)
                add_runs(cells[i].paragraphs[0], str(val), size, bold=(bold_first and i == 0))
        self.doc.add_paragraph().paragraph_format.space_after = Pt(4)
        return t

    def picture(self, path, width_cm, caption):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.space_after = Pt(4)
        p.add_run().add_picture(str(path), width=Cm(width_cm))
        label, _, text = caption.partition(":")
        c = self.doc.add_paragraph()
        c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        c.paragraph_format.space_after = Pt(12)
        r1 = c.add_run(label + ":")
        set_font(r1, 11, True)
        r2 = c.add_run(text)
        set_font(r2, 11, False)
        self.found_figs.append(caption)

    def code(self, title, source, text, note):
        self.P(f"**{title}**", after=2, keep=True, align="l")
        self.P(f"Source: {source}", size=10, italic=True, after=3, keep=True, align="l")
        t = self.doc.add_table(rows=1, cols=1)
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        c = t.rows[0].cells[0]
        shade(c, "F4F4F0")
        cell_margins(c, 80, 80, 140, 140)
        c.paragraphs[0].text = ""
        first = True
        for line in text.splitlines():
            p = c.paragraphs[0] if first else c.add_paragraph()
            first = False
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            r = p.add_run(line.replace("\t", "    ") or " ")
            set_font(r, 8, name="Courier New")
        self.P(note, size=11, before=6, after=10)

    # ---- front matter
    def cover(self):
        P = self.P
        P("Mini Project Report", 16, "c", True, after=2, before=10)
        P("On", 13, "c", after=4)
        P(C.TITLE, 20, "c", True, after=18)
        P("Submitted in partial fulfillment of academic requirements for the award of the degree of", 12, "c", after=2)
        P("Bachelor of Engineering in Computer Science and Engineering (CSIT)", 12, "c", after=14)
        P("By", 12, "c", True, after=6)
        for n, r in C.TEAM:
            P(f"**{n}**   **{r}**", 13, "c", after=2)
        P("Under Guidance of", 12, "c", after=2, before=14)
        P(f"**{C.GUIDE[0]}**", 13, "c", after=0)
        P(C.GUIDE[1], 12, "c", after=10)
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(str(ASSETS / "brand" / "college_logo.jpg"), width=Cm(3.4))
        P("DEPARTMENT OF COMPUTER SCIENCE AND ENGINEERING", 13, "c", True, after=2, before=6)
        P("MATURI VENKATA SUBBA RAO (MVSR) ENGINEERING COLLEGE", 13, "c", True, after=2)
        P("(An Autonomous Institution, Sponsored by Matrusri Education Society - Estd. 1980)", 11, "c", after=0)
        P("(Affiliated to Osmania University & Recognized by AICTE)", 11, "c", after=0)
        P("Nadergul, Balapur Mandal, Hyderabad – 501 510", 11, "c", after=4)
        P(f"**Academic Year: {C.YEAR}**", 12, "c")

    def certificate(self):
        self.doc.add_page_break()
        P = self.P
        P("MATURI VENKATA SUBBA RAO (MVSR) ENGINEERING COLLEGE", 13, "c", True, after=0)
        P("(An Autonomous Institution)", 12, "c", True, after=0)
        P("Department of Computer Science and Engineering", 11, "c", after=0)
        P("(Affiliated to Osmania University & Recognized by AICTE)", 11, "c", after=0)
        P("Nadergul, Balapur Mandal, Hyderabad – 501 510", 11, "c", after=6)
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(str(ASSETS / "brand" / "college_logo.jpg"), width=Cm(3.0))
        P("CERTIFICATE", 15, "c", True, after=8, before=6)
        names = " and ".join(f"**{n}** bearing H.T No **{r}**" for n, r in C.TEAM)
        P(f"This is to certify that the Mini Project entitled “**{C.TITLE}**”, is being submitted by {names} in partial fulfillment of academic requirements for the award "
          "of the degree of BACHELOR OF ENGINEERING in COMPUTER SCIENCE AND ENGINEERING (CSIT) from MVSR Engineering College, affiliated to OSMANIA UNIVERSITY, is a record of "
          "bonafide work carried out by them under the guidance and supervision of the faculty of the Department of CSE. The results embodied in this project report have not been "
          "submitted to any other University or Institute for the award of any degree or diploma to the best of our knowledge and belief.", 12, after=14)
        t = self.doc.add_table(rows=1, cols=3)
        cols = [("Internal Guide", [C.GUIDE[0], C.GUIDE[1]]), ("Project Coordinators", C.COORDINATORS), ("Head of the Department", [C.HOD[0]] + C.HOD[1])]
        for i, (h, lines) in enumerate(cols):
            c = t.rows[0].cells[i]
            c.paragraphs[0].text = ""
            add_runs(c.paragraphs[0], f"**{h}**", 11.5)
            for ln in lines:
                q = c.add_paragraph()
                q.paragraph_format.space_after = Pt(0)
                add_runs(q, ln, 11)
        P("External Examiner :", 12, "c", True, before=28)

    def acknowledgement(self):
        self.doc.add_page_break()
        P = self.P
        P("ACKNOWLEDGEMENT", 15, "c", True, after=14)
        P("We take this opportunity to express our profound and sincere gratitude to all those who helped us in carrying out this project successfully.", 12, after=10)
        P(f"At the very outset, we are thankful to our Principal **{C.PRINCIPAL}** and **{C.HOD[0]}**, Professor and Head, Department of Computer Science and Engineering, "
          "MVSR Engineering College, Hyderabad, for their consent to do the project work as a part of our B.E. degree (CSE). We thank them for their valuable suggestions and advice "
          "throughout our stay at the college, during our project work.", 12, after=10)
        P(f"We would like to thank our Internal Project Guide **{C.GUIDE[0]}**, {C.GUIDE[1]}, MVSR Engineering College, for the useful suggestions, guidance and encouragement.", 12, after=10)
        P("We thank the teaching and non-teaching staff of CSE for extending their support.", 12, after=10)
        P("Finally, we are thankful to our parents for their cooperation and support throughout all endeavours in our life.", 12, after=30)
        for n, r in C.TEAM:
            P(f"**{n} ({r})**", 12, "r", after=2)

    def department(self):
        self.doc.add_page_break()
        P = self.P
        P("DEPARTMENT OF COMPUTER SCIENCE ENGINEERING", 14, "l", True, after=10)
        P("VISION", 13, "l", True, after=4)
        P("To impart technical education of the highest standards, producing competent and confident engineers with the ability to use computer science knowledge to solve societal problems.", 12, after=10)
        P("MISSION", 13, "l", True, after=4)
        self.bullets(["To make the learning process exciting, stimulating and interesting.", "To impart adequate fundamental knowledge and soft skills to students.",
                      "To expose students to advanced computer technologies in order to excel in engineering practices by bringing out the creativity in students.",
                      "To develop economically feasible and socially acceptable software."])
        P("PROGRAM EDUCATIONAL OBJECTIVES (PEOs)", 13, "l", True, after=4, before=8)
        P("The Bachelor’s program in Computer Science and Engineering is aimed at preparing graduates who will:", 12, after=4)
        P("PEO-1: Achieve recognition through demonstration of technical competence for successful execution of software projects to meet customer business objectives.", 12, after=4)
        P("PEO-2: Practice life-long learning by pursuing professional certifications, higher education or research in the emerging areas of information processing and intelligent systems at a global level.", 12, after=4)
        P("PEO-3: Contribute to society by understanding the impact of computing using a multidisciplinary and ethical approach.", 12, after=8)
        P("PROGRAM SPECIFIC OUTCOMES (PSOs)", 13, "l", True, after=4, before=6)
        P("PSO-1: Demonstrate competence to build effective solutions for computational real-world problems using software and hardware across multi-disciplinary domains.", 12, after=4)
        P("PSO-2: Adapt to current computing trends for meeting the industrial and societal needs through holistic professional development leading to pioneering careers or entrepreneurship.", 12)

    def course(self):
        self.doc.add_page_break()
        P = self.P
        P("COURSE OBJECTIVES AND OUTCOMES", 14, "l", True, after=8)
        P("**COURSE NAME: MINI PROJECT**", 12, "l", after=2)
        P("**COURSE CODE: U22PW581CB**", 12, "l", after=8)
        P("**Course Objectives:**", 12, "l", after=3)
        self.numbered(["Derive requirements and technical challenges in order to solve real life problems using various platforms and programming skills.",
                       "Design the functional and system architecture for the same, develop appropriate algorithms/techniques, perform various testing.",
                       "Adopting skills to communicate effectively and to present ideas clearly and coherently in both the written and oral forms.",
                       "Acquiring collaborative skills through working in a team to achieve common goals.", "To expose students for the use of state-of-art technologies."])
        P("**Course Outcomes:**", 12, "l", after=3, before=8)
        self.table(["Code No.", "Statement (Student will be able to)"],
                   [("CO1", "Understand the steps involved in designing a project."), ("CO2", "Identify a problem; and analyze requirements."),
                    ("CO3", "Represent design flow and implement using contemporary technologies and tools."), ("CO4", "Test and deploy the applications."),
                    ("CO5", "Demonstrate qualities necessary for working in a team"), ("CO6", "Communicate effectively in both written and oral forms.")], [3, 12.2])

    def abstract(self):
        self.doc.add_page_break()
        self.P("Abstract", 15, "c", True, after=12)
        for t in C.ABSTRACT:
            self.P(t, 12, after=8)
        self.P("", after=14)
        for n, r in C.TEAM:
            self.P(f"**{n} ({r})**", 12, "r", after=2)

    def toc(self):
        self.doc.add_page_break()
        self.P("Table of Contents", 15, "c", True, after=10)
        t = self.doc.add_table(rows=1, cols=3)
        t.style = "Table Grid"
        t.autofit = False
        for i, (h, w) in enumerate((("Chapter", 2.2), ("Title & Subsections", 11.6), ("Pages", 2.0))):
            c = t.rows[0].cells[i]
            c.width = Cm(w)
            shade(c, "E3EACF")
            c.paragraphs[0].text = ""
            add_runs(c.paragraphs[0], h, 11, True)
        self._toc_table = t
        self._toc_placeholder = self.doc.add_paragraph()

    def fill_toc(self):
        t = self._toc_table
        for lvl, text in self.toc_entries:
            cells = t.add_row().cells
            for i, w in enumerate((2.2, 11.6, 2.0)):
                cells[i].width = Cm(w)
                cells[i].paragraphs[0].text = ""
                cells[i].paragraphs[0].paragraph_format.space_after = Pt(0)
            m = re.match(r"^(\d+)\.\s+(.*)$", text)
            if lvl == 1 and m:
                add_runs(cells[0].paragraphs[0], m.group(1), 10, True)
                add_runs(cells[1].paragraphs[0], m.group(2), 10, True)
            else:
                add_runs(cells[1].paragraphs[0], text, 10)
            pg = self.toc_pages.get(text, "")
            add_runs(cells[2].paragraphs[0], str(pg), 10, lvl == 1)

    def list_of_figures(self):
        self.doc.add_page_break()
        self.P("List of Figures", 15, "c", True, after=10)
        t = self.doc.add_table(rows=1, cols=2)
        t.style = "Table Grid"
        t.autofit = False
        for i, (h, w) in enumerate((("Figure", 13.8), ("Page", 2.0))):
            c = t.rows[0].cells[i]
            c.width = Cm(w)
            shade(c, "E3EACF")
            c.paragraphs[0].text = ""
            add_runs(c.paragraphs[0], h, 11, True)
        for cap in self.figs:
            cells = t.add_row().cells
            for i, w in enumerate((13.8, 2.0)):
                cells[i].width = Cm(w)
                cells[i].paragraphs[0].text = ""
                cells[i].paragraphs[0].paragraph_format.space_after = Pt(0)
            add_runs(cells[0].paragraphs[0], cap.replace(":", " –", 1), 10.5)
            add_runs(cells[1].paragraphs[0], str(self.toc_pages.get(cap, "")), 10.5)

    # ---- body
    def body(self):
        P, fig = self.P, lambda name: ASSETS / "diagrams" / f"{name}.png"
        scr = lambda name, mob=False: ASSETS / "screens" / ("mobile" if mob else "desktop") / f"{name}.png"

        self.H1("1. INTRODUCTION")
        self.H2("1.1 Problem Definition")
        for t in C.PROBLEM:
            P(t)
        self.H2("1.2 Domain Description")
        for t in C.DOMAIN:
            P(t)
        self.H2("1.3 Applications of the Project")
        P("CRATE-SCAN supports food-safety work in several practical ways. The main areas of application are:", after=8)
        for a, b in C.APPLICATIONS:
            self.titled_bullet(a, b)
        self.H2("1.4 SRS (Hardware and Software Requirements)")
        self.H3("Software Requirements")
        self.table(["Area", "Technology", "Purpose"], C.SOFTWARE, [2.6, 6.0, 7.6], 10)
        self.H3("Hardware Requirements")
        self.table(["Item", "Specification"], C.HARDWARE, [4.4, 11.8], 10.5)
        self.H3("Functional Requirements")
        self.table(["ID", "Requirement"], C.FUNCTIONAL, [1.8, 14.4], 10.5)
        self.H3("Non-Functional Requirements")
        self.table(["Quality", "Requirement"], C.NONFUNCTIONAL, [3.2, 13.0], 10.5)

        self.H1("2. DESIGN")
        self.H2("2.1 System Architecture")
        P("CRATE-SCAN follows a layered, service-oriented architecture. A Next.js website talks to a FastAPI back-end over HTTPS; the back-end uses MongoDB Atlas for data and files, "
          "Firebase Authentication for identity and a chain of AI providers for label reading. Both the website and the API run as separate Render web services, released by a GitHub Actions pipeline.")
        self.picture(fig("architecture"), 15.6, "Figure 2.1: Architecture of the project")
        for a, b in C.ARCH_COMPONENTS:
            self.titled_bullet(a, b)
        self.H3("Data Flow Overview")
        self.numbered(C.DATAFLOW)
        self.H2("2.2 Modules and Their Description")
        P("The platform consists of the following modules, each with a specific responsibility:", after=6)
        self.table(["Module", "Description"], C.MODULES, [4.4, 11.8], 10.5, bold_first=True)
        self.H2("2.3 Use-Case Design")
        P("The use-case diagram shows what each kind of user can do. Inspectors perform the inspection workflow; administrators manage the data that the workflow depends on; "
          "the Super Administrator additionally manages administrator accounts. The AI providers are external systems used for label reading and assistant answers.")
        self.picture(fig("use_case"), 15.6, "Figure 2.2: Use-case diagram")
        self.H2("2.4 Data Model")
        P("MongoDB stores documents in collections with schema validators and indexes that are created by ordered, idempotent migrations. Files are stored in GridFS buckets. "
          "The main collections and their relationships are shown below.")
        self.picture(fig("data_model"), 15.6, "Figure 2.3: Data model (MongoDB collections)")
        self.table(["Collection", "Purpose"], C.COLLECTIONS, [4.6, 11.6], 10.5, bold_first=True)
        self.H2("2.5 Inspection Workflow")
        P("An inspection moves through six guided steps. Every step saves its result, so an inspector can stop and continue later, and the final report is generated only from values the inspector has approved.")
        self.picture(fig("workflow"), 15.6, "Figure 2.4: Inspection workflow")
        self.H2("2.6 Security Design")
        P("Security is designed in layers so that no single mistake exposes data. Each request passes the layers below in order.")
        self.picture(fig("security_layers"), 15.6, "Figure 2.5: Request protection pipeline")
        self.table(["Layer", "Control"], C.SECURITY_CONTROLS, [3.4, 12.8], 10.5, bold_first=True)
        self.H2("2.7 Deployment and CI/CD")
        P("Every change goes through the same pipeline: quality checks, automated tests, security scans and a production build. The main branch is protected, so changes arrive only through pull requests "
          "with all six required checks passing; Render deploys the API and the website automatically after that.")
        self.picture(fig("cicd"), 15.6, "Figure 2.6: CI/CD pipeline")

        self.H1("3. IMPLEMENTATION")
        self.H2("3.1 Project Structure")
        P("The repository is organised so that each layer has one job. The back-end separates routers (HTTP), services (business logic) and repositories (the only code that touches the database).", after=6)
        self.code("Repository layout", "repository root", C.STRUCTURE, "The separation is enforced by an automated architecture test that fails the build if a router imports the database layer directly.")
        self.H2("3.2 Sample Code")
        for i, (title, src, rx, n, note) in enumerate(C.CODE_SNIPPETS, 1):
            self.code(f"Listing 3.{i}: {title}", src, snippet(src, rx, n), note)
        self.H2("3.3 Issues Found and Resolved During Development")
        P("A pre-production security audit and the continuous-integration runs found a number of problems. Each was reproduced, fixed, and covered by a regression test:", after=6)
        self.table(["Issue", "Impact", "Resolution"], C.ISSUES, [3.8, 5.6, 6.8], 10, bold_first=True)

        self.H1("4. TESTING AND RESULTS")
        self.H2("4.1 Test Strategy and Summary of Results")
        P("Testing is automated and layered. Each level answers a different question: do the functions work, do the screens work, can the system be attacked, and does the whole pipeline stay green.", after=6)
        self.table(["Level", "Tools", "What is covered", "Result"], C.TEST_LEVELS, [3.0, 3.6, 6.2, 3.4], 9.5, bold_first=True)
        P("Browser tests run against a real browser on both a 1440 px desktop viewport and an iPhone 14 viewport, signing in through the Firebase Auth emulator, and check that every page renders without "
          "console errors or horizontal scrolling. The AI provider is a deterministic test provider in automated runs; live providers (Gemini, NVIDIA) are covered by mocked-HTTP tests and by the "
          "diagnostics page, which calls them for real.", before=4)
        n = 1
        for title, focus, result, img, cap in C.SCREENS:
            n += 1
            self.H2(f"4.{n} {title}")
            P("**Test Focus:**", after=2, keep=True, align="l")
            self.bullets(focus, keep=True)
            P("**Result:**", after=2, before=6, keep=True, align="l")
            P(result, after=8, keep=True)
            self.picture(scr(img), 14.8, f"Figure 4.{n}: {cap}")
        n += 1
        self.H2(f"4.{n} Mobile Layout")
        P(C.MOBILE_NOTE)
        mo = ["03-inspector-dashboard", "07-findings", "11-admin-dashboard"]
        t = self.doc.add_table(rows=1, cols=3)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, name in enumerate(mo):
            c = t.rows[0].cells[i]
            c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            c.paragraphs[0].add_run().add_picture(str(scr(name, True)), width=Cm(4.8))
        self.P("**Figure 4.%d:** Mobile views – inspector dashboard, findings and administrator dashboard" % n, 11, "c", before=6, after=12)
        self.found_figs.append(f"Figure 4.{n}: Mobile views – inspector dashboard, findings and administrator dashboard")
        n += 1
        self.H2(f"4.{n} Security Testing Results")
        P("The attacker-style suite sends raw HTTP requests, ignoring the user interface. It runs against a local stack with real token verification enabled in a second instance. "
          "A summary of what was attacked and what was observed:", after=6)
        self.table(["Attack", "Result"], [
            ("Missing, malformed, forged, expired or replayed tokens on 74 protected operations", "Rejected with 401 on every route"),
            ("Pending, disabled and unverified accounts using the application", "Refused (403) on every application route"),
            ("Inspector B reading or changing inspector A's records through every inspection route", "Answered exactly like a record that does not exist"),
            ("Role escalation through profile fields, headers or the admin API", "Rejected (422 / 403)"),
            ("NoSQL operator objects and strings in query strings, bodies and path ids", "Rejected or matched literally; no widened queries, no server errors"),
            ("HTML, SVG, PHP and executable files disguised as images; pixel-bomb image", "Rejected (415 / 413); server stayed healthy"),
            ("30 parallel AI requests against a daily limit of 5", "At most 5 succeeded (atomic quota)"),
            ("Rotating X-Forwarded-For to avoid the rate limit", "Blocked after the fix (limit applied to the real client)"),
            ("Wrong origin, missing security headers, public API docs in production mode", "No CORS access for other origins; headers present; docs hidden"),
        ], [10.4, 5.8], 10)
        n += 1
        self.H2(f"4.{n} Limitations")
        self.bullets(["The reference records and compliance rules are fictional demonstration data and must be replaced with official data before any real use.",
                      "Automated tests use a deterministic AI provider; the quality of live label reading depends on the provider and on photograph quality, and providers may be temporarily unavailable.",
                      "Free hosting tiers sleep after inactivity, so the first request can take up to about a minute.",
                      "Real Google sign-in is exercised through the Firebase emulator in automated tests and manually on the deployed site."])

        self.H1("5. CONCLUSION & FUTURE ENHANCEMENTS")
        self.H2("5.1 Conclusion")
        P(C.CONCLUSION)
        self.H2("5.2 Future Enhancements")
        P("To further improve the platform, the following enhancements are proposed:", after=6)
        for a, b in C.FUTURE:
            self.titled_bullet(a, b)

        self.H1("6. BIBLIOGRAPHY")
        self.H2("6.1 References")
        for i, (name, url) in enumerate(C.BIBLIOGRAPHY, 1):
            p = P(f"{i}.  {name}", after=0, keep=True, align="l")
            p.paragraph_format.left_indent = Cm(0.8)
            q = self.doc.add_paragraph()
            q.paragraph_format.left_indent = Cm(1.4)
            q.paragraph_format.space_after = Pt(8)
            r = q.add_run(url)
            set_font(r, 11, color=RGBColor(0x1F, 0x4E, 0x9E))
            r.font.underline = True


def snippet(src: str, rx: str, n: int) -> str:
    lines = (ROOT / src).read_text().splitlines()
    idx = next(i for i, ln in enumerate(lines) if re.search(rx, ln))
    if rx == "claims_stale":
        idx -= 6
    chunk = lines[idx: idx + n]
    indent = min((len(ln) - len(ln.lstrip()) for ln in chunk if ln.strip()), default=0)
    return "\n".join(ln[indent:] if ln.strip() else "" for ln in chunk).rstrip()


def build(figs, toc_pages, path: pathlib.Path) -> Report:
    r = Report(figs, toc_pages)
    r.cover()
    r.certificate()
    r.acknowledgement()
    r.department()
    r.course()
    r.abstract()
    r.toc()
    r.list_of_figures()
    sec = r.doc.sections[0]
    numbering(sec, "lowerRoman", 1)
    page_number_footer(sec, first_blank=True)
    body = r.doc.add_section(WD_SECTION.NEW_PAGE)
    numbering(body, "decimal", 1)
    page_number_footer(body, first_blank=False)
    body.footer.is_linked_to_previous = False
    r.body()
    r.fill_toc()
    path.parent.mkdir(parents=True, exist_ok=True)
    r.doc.save(path)
    return r


def to_pdf(docx: pathlib.Path) -> pathlib.Path:
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(docx.parent), str(docx)], check=True, capture_output=True, timeout=300)
    return docx.with_suffix(".pdf")


def page_texts(pdf: pathlib.Path) -> list[str]:
    out = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    return [" ".join(p.split()).lower() for p in out.split("\f")]


def find_pages(pdf: pathlib.Path, entries: list[str]) -> dict[str, int]:
    pages = page_texts(pdf)
    start = next(i for i, t in enumerate(pages) if "1. introduction" in t and "table of contents" not in t and "list of figures" not in t)
    result = {}
    for e in entries:
        needle = " ".join(e.replace(":", ":", 1).split()).lower()
        needle = needle[:70]
        for i in range(start, len(pages)):
            if needle in pages[i]:
                result[e] = i - start + 1
                break
    return result


if __name__ == "__main__":
    tmp = HERE / "_tmp"
    tmp.mkdir(exist_ok=True)
    r0 = build([], {}, tmp / f"{NAME}.docx")
    figs = r0.found_figs
    r1 = build(figs, {}, tmp / f"{NAME}.docx")
    pdf = to_pdf(tmp / f"{NAME}.docx")
    entries = [t for _, t in r1.toc_entries] + figs
    pages = find_pages(pdf, entries)
    missing = [e for e in entries if e not in pages]
    if missing:
        print("WARNING: no page found for:", missing, file=sys.stderr)
    final = OUTDIR / f"{NAME}.docx"
    build(figs, pages, final)
    pdf2 = to_pdf(final)
    print("written", final, pdf2, "pages:", len(page_texts(pdf2)))
