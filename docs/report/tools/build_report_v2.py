"""CRATE-SCAN mini-project report, college format.

Front matter (cover … list of figures) follows the MVSR internship-report layout (banner header on every page, roman page numbers);
the chapters follow the Nexora-AI theme-based-project layout (CHAPTER n / TITLE, close-ups, results, appendix, references, abbreviations).

  python3 build_report_v2.py     # writes ../CRATE-SCAN_Mini_Project_Report.docx and .pdf

Everything the team still has to fill in or change is highlighted yellow: [[placeholders]] (shown in square brackets) and the whole
Program Outcomes / Course Objectives / Course Outcomes text. Two passes fill the table of contents with real page numbers."""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

import build_report as B
import report_content as C
from build_report import ASSETS, FONT, add_runs, field, numbering, para_border_bottom, set_font, snippet

HERE = pathlib.Path(__file__).resolve().parent
OUTDIR = HERE.parent
NAME = "CRATE-SCAN_Mini_Project_Report"
TITLE = "CRATE-SCAN"
SUBTITLE = "AI-Assisted Food Product Inspection Toolkit"
FULL = f"{TITLE} – {SUBTITLE}"
TEAM = [("DUBBAKA SATHWIK", "2451-24-751-016"), ("ESHWAROJU SAHITHI", "2451-24-751-017"), ("[[Student Name 3]]", "[[Roll No. 3]]")]
YEAR = "[[2026–2027]]"
GUIDE = "[[Guide Name]]"
GUIDE_DESIG = "[[Designation]]"
TEXT_W = 16.0

# ---------------------------------------------------------------- close-up crops (from the captured screens)
CROPS = [
    ("closeup_nav", "03-inspector-dashboard", (0, 0, 320, 470)),
    ("closeup_counters", "03-inspector-dashboard", (380, 160, 1845, 345)),
    ("closeup_banner", "03-inspector-dashboard", (380, 375, 1845, 695)),
    ("closeup_stepper", "05-verify-fields", (290, 20, 1400, 215)),
    ("closeup_field", "05-verify-fields", (310, 600, 1080, 800)),
    ("closeup_findings", "07-findings", (290, 545, 1395, 710)),
    ("closeup_landing_nav", "01-landing", (230, 5, 1620, 105)),
]


def make_crops() -> None:
    from PIL import Image

    out = ASSETS / "screens" / "closeups"
    out.mkdir(exist_ok=True)
    for name, src, box in CROPS:
        Image.open(ASSETS / "screens" / "desktop" / f"{src}.png").convert("RGB").crop(box).save(out / f"{name}.png")


def HL(p, text, size=12, bold=False, italic=False):
    r = p.add_run(text)
    set_font(r, size, bold, italic)
    r.font.highlight_color = WD_COLOR_INDEX.YELLOW
    return r


class Report2(B.Report):
    def __init__(self, toc_pages, figs, tables, known):
        super().__init__(figs, toc_pages)
        self.known = known
        self.tables_l = tables
        self.found_tables: list[str] = []
        self.entries: list[tuple[int, str, str]] = []  # (level, display text, search text)
        s = self.doc.sections[0]
        s.left_margin = s.right_margin = Cm(2.5)
        s.top_margin, s.bottom_margin = Cm(2.0), Cm(2.0)
        s.header_distance, s.footer_distance = Cm(0.6), Cm(0.9)
        self.fig = lambda n: ASSETS / "diagrams" / f"{n}.png"
        self.scr = lambda n, mob=False: ASSETS / "screens" / ("mobile" if mob else "desktop") / f"{n}.png"
        self.cu = lambda n: ASSETS / "screens" / "closeups" / f"{n}.png"

    # ---- header / footer
    def header(self, section, on=True):
        for h in (section.header, section.first_page_header):
            h.is_linked_to_previous = False
            for p in list(h.paragraphs)[1:]:
                p._element.getparent().remove(p._element)
            p0 = h.paragraphs[0]
            for r in list(p0.runs):
                r._element.getparent().remove(r._element)
            if not on:
                continue
            p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p0.paragraph_format.space_after = Pt(0)
            p0.add_run().add_picture(str(ASSETS / "brand" / "header_banner.png"), width=Cm(TEXT_W))
            p1 = h.add_paragraph()
            p1.paragraph_format.space_after = Pt(2)
            set_font(p1.add_run(" "), 4)

    def footer_plain(self, section, show=True):
        for f in (section.footer, section.first_page_footer):
            f.is_linked_to_previous = False
            p = f.paragraphs[0]
            for r in list(p.runs):
                r._element.getparent().remove(r._element)
        p = section.footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if show:
            r = p.add_run()
            set_font(r, 11)
            field(r, "PAGE")

    def footer_body(self, section):
        for f in (section.footer, section.first_page_footer):
            f.is_linked_to_previous = False
        p = section.footer.paragraphs[0]
        p.style = self.doc.styles["Normal"]
        for r in list(p.runs):
            r._element.getparent().remove(r._element)
        pf = p.paragraph_format
        pf.tab_stops.add_tab_stop(Cm(TEXT_W / 2), WD_TAB_ALIGNMENT.CENTER)
        pf.tab_stops.add_tab_stop(Cm(TEXT_W), WD_TAB_ALIGNMENT.RIGHT)
        for txt in ("Dept of CSE-Allied\t[", None, "]\tCRATE-SCAN"):
            r = p.add_run(txt) if txt else p.add_run()
            set_font(r, 10)
            if txt is None:
                field(r, "PAGE")

    # ---- small blocks
    def center_title(self, text, after=10, size=14, before=0):
        return self.P(text, size, "c", True, after=after, before=before, keep=True)

    def sign_row(self, cells, size=11.5):
        t = self.doc.add_table(rows=1, cols=len(cells))
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, lines in enumerate(cells):
            c = t.rows[0].cells[i]
            c.paragraphs[0].text = ""
            for j, ln in enumerate(lines):
                q = c.paragraphs[0] if j == 0 else c.add_paragraph()
                q.paragraph_format.space_after = Pt(0)
                q.alignment = WD_ALIGN_PARAGRAPH.CENTER
                add_runs(q, ln, size, bold=(j == 0))
        return t

    def tbl(self, headers, rows, widths, caption, size=10.5, bold_first=False):
        self.table(headers, rows, widths, size, bold_first=bold_first)
        label, _, text = caption.partition(":")
        c = self.doc.add_paragraph()
        c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        c.paragraph_format.space_after = Pt(12)
        c.paragraph_format.space_before = Pt(0)
        set_font(c.add_run(label + ":"), 11, True)
        set_font(c.add_run(text), 11, False)
        self.found_tables.append(caption)

    def cmd(self, lines):
        for ln in lines:
            p = self.doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(1.2)
            p.paragraph_format.space_after = Pt(1)
            set_font(p.add_run(ln), 10, name="Courier New")
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def chapter(self, num, title):
        h = self.doc.add_heading("", 1)
        h.alignment = WD_ALIGN_PARAGRAPH.CENTER
        h.paragraph_format.page_break_before = True
        h.paragraph_format.space_after = Pt(14)
        r1 = h.add_run(f"CHAPTER {num}") if num else h.add_run(title)
        set_font(r1, 15, True, color=RGBColor(0, 0, 0))
        if num:
            r1.add_break()
            r2 = h.add_run(title)
            set_font(r2, 15, True, color=RGBColor(0, 0, 0))
        disp = f"Chapter {num}: {title.title()}" if num else title.title()
        self.entries.append((1, disp, " ".join(((f"chapter {num} " if num else "") + title).split()).lower()))

    def section(self, text):
        h = self.doc.add_heading("", 2)
        set_font(h.add_run(text), 13, True, color=RGBColor(0, 0, 0))
        h.paragraph_format.space_before = Pt(12)
        self.entries.append((2, text, text.lower()))
        return h

    def sub(self, text):
        h = self.doc.add_heading("", 3)
        set_font(h.add_run(text), 12, True, color=RGBColor(0, 0, 0))
        return h

    def front_page(self, title, new_page=True, size=14):
        if new_page:
            self.doc.add_page_break()
        self.center_title(title, 12, size)

    # ---- front matter
    def cover(self):
        P = self.P
        P("MINI PROJECT REPORT", 14, "c", True, after=3, before=14)
        P("ON", 11, "c", True, after=3)
        P(TITLE, 22, "c", True, after=2)
        P(SUBTITLE, 15, "c", True, after=8)
        P("Submitted in partial fulfilment of the requirements for the award of the degree of", 11, "c", italic=True, after=3)
        P("BACHELOR OF ENGINEERING (B.E.)", 12, "c", True, after=2)
        P("IN", 11, "c", True, after=2)
        P("COMPUTER SCIENCE AND INFORMATION TECHNOLOGY (CSIT)", 12, "c", True, after=8)
        P("BY", 11, "c", True, after=4)
        for n, r in TEAM:
            P(f"**{n}**", 13, "c", after=0)
            P(f"**({r})**", 12, "c", after=5)
        P(f"Under the guidance of **{GUIDE}**, {GUIDE_DESIG}", 12, "c", after=8, before=2)
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(4)
        p.add_run().add_picture(str(ASSETS / "brand" / "college_logo_round.png"), width=Cm(2.6))
        P("Department of Computer Science and Engineering (Allied)", 11, "c", True, after=1)
        P("MVSR ENGINEERING COLLEGE", 12, "c", True, after=1)
        P("(An Autonomous Institution)", 10, "c", after=0)
        P("(Affiliated to Osmania University & Recognized by AICTE)", 10, "c", after=0)
        P("Nadergul, Saroornagar Mandal, Hyderabad – 501 510", 10, "c", after=5)
        P(f"**{YEAR}**", 12, "c", True)

    def certificate(self):
        self.center_title("CERTIFICATE", 14, 14, 6)
        names = ", ".join(f"**{n}** ({r})" for n, r in TEAM[:2]) + f" and **{TEAM[2][0]}** ({TEAM[2][1]})"
        self.P(f"This is to certify that the mini project work entitled “**{FULL}**” is a bonafide work carried out by {names} in partial fulfilment of the requirements for the award "
               f"of the degree of Bachelor of Engineering (B.E.) in Computer Science and Information Technology (CSIT) from MVSR Engineering College, Hyderabad, during the academic year "
               f"{YEAR}, under our guidance and supervision.", 12, after=10)
        self.P("The results embodied in this report have not been submitted to any other university or institute for the award of any degree or diploma.", 12, after=40)
        self.sign_row([["Project Guide", GUIDE, GUIDE_DESIG, "Department of CSE (Allied)"],
                       ["Head of the Department", "Dr. Rajesh H. Kulkarni", "Professor & Head", "Department of CSE (Allied)"]])
        self.P("", after=26)
        self.sign_row([["Mini Project Coordinators", "[[Coordinator 1]], [[Designation]]", "[[Coordinator 2]], [[Designation]]", "Department of CSE (Allied)"]])
        self.P("External Examiner", 12, "c", True, before=40)

    def declaration(self):
        self.front_page("DECLARATION")
        self.P(f"We hereby declare that the mini project report entitled “**{FULL}**”, submitted to the Department of Computer Science and Engineering (Allied), MVSR Engineering College, "
               f"Hyderabad, is a record of bonafide work done by us under the guidance of {GUIDE}, {GUIDE_DESIG}. The report is based on the work done entirely by us and has not been copied "
               "from any other source. The results embodied in this report have not been submitted to any other university or institute for the award of any degree or diploma.", 12, after=60)
        self.sign_row([[n, f"({r})"] for n, r in TEAM])

    def acknowledgement(self):
        self.front_page("ACKNOWLEDGEMENT")
        P = self.P
        P("We would like to express our sincere gratitude to everyone who supported and guided us during this mini project.", after=9)
        P("We are thankful to **Dr. Rajesh H. Kulkarni**, Professor and Head of the Department, Department of Computer Science and Engineering (Allied), and to our Principal, "
          f"**{C.PRINCIPAL}**, MVSR Engineering College, for providing the opportunity and the facilities required to complete this project.", after=9)
        P("We sincerely thank **Dr. B. Janaiah**, Senior Assistant Professor and Associate Head of the CSIT Department, for the constant support and encouragement.", after=9)
        P("We are grateful to the Mini Project Coordinators, [[Coordinator 1]] and [[Coordinator 2]], for coordinating the project work and for the timely guidance and support at every step.", after=9)
        P(f"We express our heartfelt thanks to our Project Guide, **{GUIDE}**, {GUIDE_DESIG}, for the valuable guidance, suggestions and encouragement at every stage of this project and "
          "in the preparation of this report.", after=9)
        P("We also thank all the teaching and non-teaching staff of the department for their help.", after=9)
        P("Finally, we thank our parents and friends for their encouragement and support throughout the work.", after=26)
        for n, r in TEAM:
            P(f"**{n}** ({r})", 12, "r", after=2)

    def vision(self):
        self.front_page("VISION AND MISSION")
        P = self.P
        P("Vision", 12.5, "l", True, after=3)
        P("To impart technical education of the highest standards, producing competent and confident engineers with an ability to use computer science knowledge to solve societal problems.", after=8)
        P("Mission", 12.5, "l", True, after=3)
        self.numbered(["To make the learning process exciting, stimulating and interesting.", "To impart adequate fundamental knowledge and soft skills to students.",
                       "To expose students to advanced computer technologies in order to excel in engineering practices by bringing out creativity in students.",
                       "To develop economically feasible and socially acceptable software."])
        self.center_title("PROGRAMME EDUCATIONAL OBJECTIVES (PEOs)", 8, 13, 16)
        P("The Bachelor's program in Computer Science & Information Technology is aimed at preparing graduates who will:", after=4)
        self.numbered(["Excel in applying computer science and IT principles to develop innovative solutions and keep up with technological advancements.",
                       "Exhibit leadership, effective communication, and professional ethics in their careers.",
                       "Engage in lifelong learning and contribute to society by addressing ethical, societal, and environmental issues."])

    def outcomes(self):
        self.front_page("PROGRAM OUTCOMES (POs)")
        self.P("{{PO text — to be replaced with the current Program Outcomes}}".replace("{{", "").replace("}}", ""), 10, "c", italic=True, after=4)
        pos = [("PO1", "Engineering Knowledge", "Apply knowledge of mathematics, natural science, computing, engineering fundamentals and an engineering specialization as specified in WK1 to WK4 respectively to the solution of complex engineering problems."),
               ("PO2", "Problem Analysis", "Identify, formulate, review research literature and analyze complex engineering problems reaching substantiated conclusions with consideration for sustainable development. (WK1 to WK4)"),
               ("PO3", "Design/Development of Solutions", "Design creative solutions for complex engineering problems and design/develop systems/components/processes to meet identified needs with consideration for the public health and safety, whole-life cost, net zero carbon, culture, society and environment as required. (WK5)"),
               ("PO4", "Conduct Investigations of Complex Problems", "Conduct investigations of complex engineering problems using research-based knowledge including design of experiments, modelling, analysis & interpretation of data to provide valid conclusions. (WK8)"),
               ("PO5", "Engineering Tool Usage", "Create, select and apply appropriate techniques, resources and modern engineering & IT tools, including prediction and modelling recognizing their limitations to solve complex engineering problems. (WK2 and WK6)"),
               ("PO6", "The Engineer and The World", "Analyze and evaluate societal and environmental aspects while solving complex engineering problems for its impact on sustainability with reference to economy, health, safety, legal framework, culture and environment. (WK1, WK5, and WK7)"),
               ("PO7", "Ethics", "Apply ethical principles and commit to professional ethics, human values, diversity and inclusion; adhere to national & international laws. (WK9)"),
               ("PO8", "Individual and Collaborative Team work", "Function effectively as an individual, and as a member or leader in diverse/multi-disciplinary teams."),
               ("PO9", "Communication", "Communicate effectively and inclusively within the engineering community and society at large, such as being able to comprehend and write effective reports and design documentation, make effective presentations considering cultural, language, and learning differences."),
               ("PO10", "Project Management and Finance", "Apply knowledge and understanding of engineering management principles and economic decision-making and apply these to one's own work, as a member and leader in a team, and to manage projects and in multidisciplinary environments."),
               ("PO11", "Life-Long Learning", "Recognize the need for, and have the preparation and ability for i) independent and life-long learning ii) adaptability to new and emerging technologies and iii) critical thinking in the broadest context of technological change. (WK8)")]
        for code, head, txt in pos:
            p = self.doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            pf = p.paragraph_format
            pf.left_indent, pf.first_line_indent, pf.space_after, pf.line_spacing = Cm(1.6), Cm(-1.6), Pt(5), 1.1
            HL(p, f"{code}:\t", 11, True)
            HL(p, f"{head}: ", 11, True)
            HL(p, txt, 11)
            pf.tab_stops.add_tab_stop(Cm(1.6))

    def course(self):
        self.front_page("COURSE OBJECTIVES")
        objs = ["Derive requirements and technical challenges in order to solve real life problems using various platforms and programming skills.",
                "Design the functional and system architecture for the same, develop appropriate algorithms/techniques, perform various testing.",
                "Adopting skills to communicate effectively and to present ideas clearly and coherently in both the written and oral forms.",
                "Acquiring collaborative skills through working in a team to achieve common goals.", "To expose students for the use of state-of-art technologies."]
        for i, t in enumerate(objs, 1):
            p = self.doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.left_indent, p.paragraph_format.first_line_indent = Cm(1.2), Cm(-0.7)
            p.paragraph_format.space_after, p.paragraph_format.line_spacing = Pt(4), 1.15
            HL(p, f"{i}.  {t}")
        self.center_title("COURSE OUTCOMES", 8, 14, 16)
        p = self.doc.add_paragraph()
        HL(p, "On completion of this course, the student will be able to:")
        cos = [("CO1", "Understand the steps involved in designing a project."), ("CO2", "Identify a problem; and analyze requirements."),
               ("CO3", "Represent design flow and implement using contemporary technologies and tools."), ("CO4", "Test and deploy the applications."),
               ("CO5", "Demonstrate qualities necessary for working in a team."), ("CO6", "Communicate effectively in both written and oral forms.")]
        for c, t in cos:
            q = self.doc.add_paragraph()
            q.paragraph_format.left_indent, q.paragraph_format.first_line_indent, q.paragraph_format.space_after = Cm(1.6), Cm(-1.2), Pt(4)
            HL(q, f"{c}:  {t}")

    def certifications(self):
        pages = [("DUBBAKA SATHWIK", "sathwik", False), ("ESHWAROJU SAHITHI", "sahithi", False), (TEAM[2][0], "sathwik", True)]
        for i, (who, key, ph) in enumerate(pages):
            self.doc.add_page_break()
            if i == 0:
                self.center_title("COURSE CERTIFICATIONS", 6, 14)
            if ph:
                p = self.doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_after = Pt(4)
                HL(p, "Certificates of [Student Name 3] – replace the two images below with this student's certificates", 11, True)
            else:
                self.P(f"Certificates of **{who}**", 11.5, "c", after=4)
            for n in (1, 2):
                p = self.doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_after = Pt(6)
                p.add_run().add_picture(str(ASSETS / "certs" / f"{key}_{n}.png"), height=Cm(8.2))

    def abstract(self):
        self.front_page("ABSTRACT", size=14)
        for t in C.ABSTRACT:
            self.P(t, 12, after=8)

    FEATURES = [("Google-only sign-in with approval", "New accounts sign in with Google and wait for an administrator to approve them; roles are assigned by administrators and cannot be chosen at sign-in."),
                ("Role-based access", "Inspector, administrator and Super Administrator roles are checked on the server for every request; other users' data is never reachable."),
                ("Guided six-step inspection", "Photographs, verification, AI review, findings, decision and report; every step is saved so work can be continued later."),
                ("Photograph handling", "Up to five photographs per inspection with type, size, pixel and quality checks; originals are deleted once the report is saved."),
                ("AI label reading", "A vision AI model reads 22 label fields with a confidence value for each; providers are tried in order with retry and fallback."),
                ("Field verification", "The inspector confirms or corrects every value; the AI value is kept beside the correction for accountability."),
                ("Reference matching and rules", "Approved values are matched against product, manufacturer and licence records and checked against configurable, versioned compliance rules."),
                ("Findings with evidence", "Each finding shows the rule, expected and found values, severity and the photograph evidence; the inspector accepts, dismisses or corrects it."),
                ("13-section PDF report", "A structured report with photographs, values, findings, decisions and disclaimers, available for preview, download and print."),
                ("History and export", "Search and filter past inspections and export them to CSV or Excel with protection against formula injection."),
                ("Ask AI assistant", "Context-aware questions about labelling rules and the current inspection, with optional internet research."),
                ("Product proposals", "Inspectors propose unknown products; administrators review and approve them into the reference database."),
                ("Administrator console", "User approval, reference records, compliance rules, analytics, read-only audit log, diagnostics and site settings."),
                ("System diagnostics", "Live checks of the database, file storage, Firebase and every AI provider, with the real reason and a hint when something fails."),
                ("Responsive interface", "Phone, tablet and desktop layouts with a bottom tab bar on phones, verified by automated browser tests.")]

    def features(self):
        self.front_page("SYSTEM FEATURES", size=14)
        for i, (a, b) in enumerate(self.FEATURES, 1):
            self.P(f"**{i}. {a}**", 12, "l", after=1, keep=True)
            self.P(b, 12, after=6)

    def dotted(self, text, page, size=11, bold=False, indent=0.0):
        p = self.doc.add_paragraph()
        pf = p.paragraph_format
        pf.space_after, pf.space_before, pf.line_spacing = Pt(1.5), Pt(0), 1.0
        pf.left_indent = Cm(indent)
        pf.tab_stops.add_tab_stop(Cm(TEXT_W), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        r = p.add_run(f"{text}\t{page}")
        set_font(r, size, bold)

    def toc_front(self, front):
        self.doc.add_page_break()
        self.center_title("TABLE OF CONTENTS", 10)
        for text in front:
            self.dotted(text, self.toc_pages.get(text, ""), 11)
        self.P("", after=2)
        for lvl, disp, _ in self.known:
            self.dotted(disp, self.toc_pages.get(disp, ""), 11 if lvl == 2 else 11.5, bold=(lvl == 1), indent=0.6 if lvl == 2 else 0)

    def lists(self):
        self.front_page("LIST OF TABLES")
        for cap in self.tables_l:
            label, _, text = cap.partition(":")
            self.dotted(f"{label}:{text}", self.toc_pages.get(cap, ""), 11)
        self.front_page("LIST OF FIGURES")
        for cap in self.figs:
            self.dotted(cap, self.toc_pages.get(cap, ""), 11)

    # ---- body: Nexora-style chapters
    def body(self):
        P, fig, scr, cu = self.P, self.fig, self.scr, self.cu
        # ---------------- chapter 1
        self.chapter(1, "INTRODUCTION")
        self.section("1.1 Detailed Problem Statement")
        for t in C.PROBLEM:
            P(t)
        self.section("1.2 Analysis of Existing Systems")
        P("Food-product inspection today relies on methods that were not designed for fast, evidence-based field work:", after=4)
        self.titled_bullet("Manual paper or spreadsheet checklists", "Inspectors read every declaration by eye and tick a form. The work is slow, differs from inspector to inspector and leaves weak evidence behind.")
        self.titled_bullet("Generic OCR and chat tools", "General text-recognition apps or AI chatbots can read a label, but they do not know the regulations, give no confidence per field, do not keep the inspector's correction beside the AI value and offer no audit trail.")
        self.titled_bullet("Unstructured reference data", "Licence and product records are held in separate lists, so matching a label against them is manual and rarely documented.")
        self.titled_bullet("No safeguards for sensitive data", "Photographs and reports are often shared through chat applications or personal storage, without role-based access or retention rules.")
        self.section("1.3 Proposed System")
        P("CRATE-SCAN is a role-based web application that guides the inspector through six steps – photograph, read, verify, analyse, decide and report – while keeping the inspector in control. "
          "A vision AI model reads 22 label fields with a confidence for each; the inspector confirms or corrects them; the system matches the approved values with reference records and a configurable rule set and "
          "presents findings with evidence; and a 13-section PDF report is produced. Key features of the proposed system:", after=4)
        self.bullets(["**Human in control:** the AI only suggests; every finding and the final classification are decided by the inspector.",
                      "**Resilient AI chain:** ordered providers (Gemini, then NVIDIA, with optional OCR) with retry, fallback and an explicit incomplete state.",
                      "**Secure by design:** Google sign-in with administrator approval, server-checked roles, owner-scoped data and an append-only audit log.",
                      "**Evidence retained:** AI value, inspector correction, rule and photograph evidence are stored together and printed in the report.",
                      "**Field-ready:** mobile-first layout with automatic saving of every step."])
        self.section("1.4 Comprehensive Project Scope")
        P("The project delivers a working, tested web application for food-safety inspectors and administrators, covering the whole path from photograph to report together with the administrator console that keeps the "
          "reference data, rules and users up to date. It is decision support for authorised inspection work and does not replace official laboratory testing or the authority of the inspector. "
          "The main areas of application are:", after=4)
        for a, b in C.APPLICATIONS:
            self.titled_bullet(a, b)
        self.section("1.5 Project Objectives")
        self.bullets(["**Faster inspection:** cut the time needed to inspect and document a packaged product.",
                      "**Transparent AI:** show each AI value with its confidence and make correction easy.",
                      "**Inspector accountability:** record who decided what, and keep the AI suggestion next to the decision.",
                      "**Data protection:** keep photographs and reports private to their owner; delete originals after the report.",
                      "**Reliability:** keep working when an AI provider is slow or unavailable.",
                      "**Assurance:** verify the system with unit, browser, attack-style and static-analysis tests on every change."])

        # ---------------- chapter 2
        self.chapter(2, "SYSTEM REQUIREMENT SPECIFICATIONS")
        self.section("2.1 Software Requirements")
        self.tbl(["Area", "Technology", "Purpose"], C.SOFTWARE, [2.6, 6.0, 7.4], "Table 2.1: Software requirements", 10)
        self.section("2.2 Hardware Requirements")
        self.tbl(["Item", "Specification"], C.HARDWARE, [4.4, 11.6], "Table 2.2: Hardware requirements", 10.5)
        self.section("2.3 Functional and Non-Functional Requirements")
        self.tbl(["ID", "Requirement"], C.FUNCTIONAL, [1.8, 14.2], "Table 2.3: Functional requirements", 10.5)
        self.tbl(["Quality", "Requirement"], C.NONFUNCTIONAL, [3.2, 12.8], "Table 2.4: Non-functional requirements", 10.5)
        self.section("2.4 Detailed System Architecture")
        P("The application uses a layered, service-oriented architecture. A Next.js website talks to a FastAPI back-end over HTTPS; the back-end uses MongoDB Atlas for data and files, Firebase "
          "Authentication for identity and a chain of AI providers for label reading. Both the website and the API run as separate Render web services, released by a GitHub Actions pipeline.")
        self.picture(fig("architecture"), 15.4, "Figure 2.1: CRATE-SCAN System Architecture")
        for a, b in C.ARCH_COMPONENTS:
            self.titled_bullet(a, b)
        self.sub("Data Flow Overview")
        self.numbered(C.DATAFLOW)

        # ---------------- chapter 3
        self.chapter(3, "DESIGN & IMPLEMENTATION")
        self.section("3.1 Features List")
        for i, (a, b) in enumerate(self.FEATURES[:8], 1):
            self.titled_bullet(a, b)
        P("The remaining features are listed under System Features at the start of this report.")
        self.section("3.2 Modules Description")
        self.tbl(["Module", "Description"], C.MODULES, [4.4, 11.6], "Table 3.1: Modules of CRATE-SCAN", 10.5, bold_first=True)
        self.section("3.3 UML Diagrams")
        self.sub("Use Case Diagram")
        P("The use-case diagram shows what each kind of user can do. Inspectors perform the inspection workflow; administrators manage the data the workflow depends on; the Super Administrator additionally "
          "manages administrator accounts. The AI providers are external systems used for label reading and assistant answers.")
        self.picture(fig("use_case"), 15.4, "Figure 3.1: CRATE-SCAN Use Case Diagram")
        self.sub("Activity Diagram (Inspection Workflow)")
        P("An inspection moves through six guided steps. Every step saves its result, so an inspector can stop and continue later, and the final report is generated only from values the inspector has approved.")
        self.picture(fig("workflow"), 15.4, "Figure 3.2: Activity Diagram for the Inspection Workflow")
        self.sub("Class Diagram (Data Model)")
        P("MongoDB stores documents in collections with schema validators and indexes created by ordered, idempotent migrations; files live in GridFS buckets. The collections and their relationships act as the class model of the system.")
        self.picture(fig("data_model"), 15.4, "Figure 3.3: Data Model (MongoDB Collections)")
        self.tbl(["Collection", "Purpose"], C.COLLECTIONS, [4.6, 11.4], "Table 3.2: Collections and their purpose", 10.5, bold_first=True)
        self.sub("Security Layers")
        P("Security is designed in layers so that no single mistake exposes data. Each request passes the layers below in order.")
        self.picture(fig("security_layers"), 15.4, "Figure 3.4: Request Protection Pipeline")
        self.tbl(["Layer", "Control"], C.SECURITY_CONTROLS, [3.4, 12.6], "Table 3.3: Security controls by layer", 10.5, bold_first=True)

        self.section("3.4 Environmental Setup")
        P("The steps below set up a development machine and start the complete application locally (database, Firebase Auth emulator, API and website).", after=4)
        self.sub("Step 1: Install the Required Tools")
        self.numbered(["Install Visual Studio Code from https://code.visualstudio.com (the editor used for development) and Git from https://git-scm.com.",
                       "Install Node.js 22 and pnpm 10, Python 3.12 and the uv package manager, Java 21 (needed by the Firebase emulator) and Docker (runs a local MongoDB).",
                       "Install the Firebase command-line tools with the command shown below."])
        self.cmd(["npm i -g firebase-tools"])
        self.sub("Step 2: Get the Source Code")
        self.cmd(["git clone https://github.com/DubbakaSathwik/Food_inspection_toolkit.git", "cd Food_inspection_toolkit"])
        self.sub("Step 3: Install the Dependencies")
        self.cmd(["(cd backend && uv sync) && (cd frontend && pnpm install)"])
        self.sub("Step 4: Configure and Start")
        P("For local work no cloud account is needed: the helper script starts a local MongoDB, the Firebase Auth emulator, the API and the website together and loads demonstration data.", after=4)
        self.cmd(["scripts/local-stack.sh --fresh"])
        self.sub("Step 5: Run the Tests")
        self.cmd(["cd backend && uv run pytest --cov=app", "cd frontend && pnpm test && pnpm exec playwright test"])
        P("For a deployed environment, the secrets (database connection string, Firebase service account and AI provider keys) are set only in the hosting dashboard and never committed to the repository.")

        self.section("3.5 Implementation & Methodology Steps")
        self.numbered(["**Requirement analysis:** the problem, users, label fields and regulations were studied and written as functional and non-functional requirements.",
                       "**Design:** architecture, use cases, data model and the six-step workflow were drawn before coding.",
                       "**Back-end:** a layered FastAPI service (routers → services → repositories) with strict Pydantic models, MongoDB migrations and Firebase token verification.",
                       "**AI integration:** a provider chain with retry and fallback, confidence per field, and a deterministic test provider for automated runs.",
                       "**Front-end:** a mobile-first Next.js interface for inspectors and administrators.",
                       "**Testing and security audit:** unit, browser and attack-style tests; every issue found was fixed and covered by a regression test.",
                       "**Deployment:** a protected main branch, six required checks and automatic deployment of the API and website after the checks pass."])
        self.sub("Project Structure")
        self.code("Repository layout", "repository root", C.STRUCTURE, "The separation is enforced by an automated architecture test that fails the build if a router imports the database layer directly.")
        self.sub("CI/CD Pipeline")
        self.picture(fig("cicd"), 15.4, "Figure 3.5: CI/CD and Deployment Pipeline")

        # ---------------- chapter 4
        self.chapter(4, "DETAILED PAGE FEATURES & CLOSE-UPS")
        self.section("4.1 Home Page Breakdown")
        P("The public home page introduces the product and leads to sign-in. It loads without errors on desktop and mobile and has no horizontal scrolling.", after=4)
        self.picture(scr("01-landing"), 14.6, "Figure 4.1: Home Page of CRATE-SCAN")
        self.bullets(["**Top bar:** logo, Home / Features / How It Works / About links and the Open app button.", "**Hero:** the headline, a one-paragraph description, and the Get Started and Explore Features buttons beside the product image.",
                      "**Capability strip:** Scan Products, Check Compliance and Generate Reports."])
        self.section("4.2 Close-up Visuals: Logo & Navigation Panel")
        self.picture(cu("closeup_nav"), 5.6, "Figure 4.2: Brand Logo and Navigation Sidebar")
        P("The sidebar shows the logo and the six destinations of an inspector: Dashboard, New Inspection, Inspection History, Product Proposals, Ask AI and Profile. The current page is highlighted. On phones the sidebar becomes a bottom tab bar.")
        self.section("4.3 Close-up Visuals: Dashboard Counters and Start Panel")
        self.picture(cu("closeup_counters"), 15.0, "Figure 4.3: Summary Counters of the Inspector Dashboard")
        P("The four counters – total inspections, completed inspections, pending reviews and submitted proposals – are calculated only from the signed-in inspector's own records.")
        self.picture(cu("closeup_banner"), 15.0, "Figure 4.4: Start a New Inspection Panel")
        self.section("4.4 Close-up Visuals: Step Indicator and Field Verification")
        self.picture(cu("closeup_stepper"), 15.0, "Figure 4.5: Five-Step Inspection Progress Indicator")
        P("The indicator shows the steps Photographs, Verify Fields, AI Review, Findings and Report; completed steps are ticked and the current step is numbered.")
        self.picture(cu("closeup_field"), 11.5, "Figure 4.6: Extracted Field with AI Confidence")
        P("Each extracted field shows its AI confidence, the photograph it was read from, an Auto-confirmed tag for high-confidence values, and an Edit button for corrections.")
        self.section("4.5 Close-up Visuals: Findings Summary")
        self.picture(cu("closeup_findings"), 15.0, "Figure 4.7: Analysis Summary Cards on the Findings Page")
        P("Five cards summarise the analysis: extraction, reference match, licence check, packaging comparison and labelling rules. Demonstration records are labelled as such and never presented as government verification.")
        self.section("4.6 Detailed Button Mechanics & Core Functions")
        self.tbl(["Control", "What it does"], [
            ("Continue with Google", "Opens the Google sign-in; the server verifies the token and creates a pending profile for a new user."),
            ("Create Inspection", "Creates a draft inspection as soon as a category is chosen; every later step saves automatically."),
            ("Confirm all remaining", "Confirms every field the inspector has not changed; high-confidence fields were already auto-confirmed."),
            ("Replay AI reading", "Runs the label reading again, for example after a provider outage."),
            ("Edit (field)", "Lets the inspector correct a value; the AI value is kept beside the correction."),
            ("Accept / Dismiss / Correct (finding)", "Records the inspector's decision on a finding with an optional note."),
            ("Download PDF", "Generates the 13-section report from approved values only; original photographs are then deleted."),
        ], [5.0, 11.0], "Table 4.1: Main buttons and their behaviour", 10.5, bold_first=True)
        P("The core functions behind these controls – owner-scoped data access, token verification, the AI provider chain and report generation – are listed in the Appendix.")

        # ---------------- chapter 5
        self.chapter(5, "RESULTS & DISCUSSION")
        n = 0
        for title, focus, result, img, cap in C.SCREENS:
            if img == "01-landing":
                continue
            n += 1
            self.section(f"5.{n} {title}")
            P("**Test Focus:**", after=2, keep=True, align="l")
            self.bullets(focus, keep=True)
            P("**Result:**", after=2, before=6, keep=True, align="l")
            P(result, after=8, keep=True)
            self.picture(scr(img), 14.6, f"Figure 5.{n}: {cap}")
        n += 1
        self.section(f"5.{n} Responsive Mobile Viewport")
        P(C.MOBILE_NOTE)
        t = self.doc.add_table(rows=1, cols=3)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, name in enumerate(["03-inspector-dashboard", "07-findings", "11-admin-dashboard"]):
            c = t.rows[0].cells[i]
            c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            c.paragraphs[0].add_run().add_picture(str(scr(name, True)), width=Cm(4.6))
        cap = f"Figure 5.{n}: Mobile Views – Inspector Dashboard, Findings and Administrator Dashboard"
        self.P(f"**Figure 5.{n}:** {cap.partition(': ')[2]}", 11, "c", before=6, after=12)
        self.found_figs.append(cap)
        n += 1
        self.section(f"5.{n} Validation & Testing")
        P("Testing is automated and layered. Each level answers a different question: do the functions work, do the screens work, can the system be attacked, and does the whole pipeline stay green.", after=6)
        self.tbl(["Level", "Tools", "What is covered", "Result"], C.TEST_LEVELS, [2.9, 3.4, 6.2, 3.5], f"Table 5.1: Test levels and results", 9.5, bold_first=True)
        self.sub("System Test Matrix")
        self.tbl(["TC", "Scenario", "Expected result", "Status"], [
            ("TC-1", "New Google account signs in", "Waits on the pending page until an administrator approves", "PASS"),
            ("TC-2", "Inspector opens an administrator page", "Access refused (403)", "PASS"),
            ("TC-3", "Upload a valid photograph / a disguised executable", "Valid file accepted; disguised file rejected (415)", "PASS"),
            ("TC-4", "AI reading, then provider outage", "22 fields with confidence; outage shows an incomplete state with retry", "PASS"),
            ("TC-5", "Edit and confirm extracted fields", "Correction saved; AI value retained beside it", "PASS"),
            ("TC-6", "Run reference matching and rules", "Findings with severity, expected/found values and evidence", "PASS"),
            ("TC-7", "Generate the report", "13-section PDF; original photographs deleted afterwards", "PASS"),
            ("TC-8", "Inspector B requests Inspector A's inspection", "Answered exactly like a record that does not exist", "PASS"),
            ("TC-9", "Rotate X-Forwarded-For to evade the rate limit", "Requests still limited by the real client address", "PASS"),
            ("TC-10", "Administrator edits a rule / imports records", "New rule version; change written to the audit log", "PASS"),
            ("TC-11", "Open every page at 390 px width", "No horizontal scrolling and no console errors", "PASS"),
            ("TC-12", "30 parallel AI requests against a limit of 5", "At most 5 succeed (atomic quota)", "PASS"),
        ], [1.4, 5.6, 7.2, 1.8], "Table 5.2: System Test Matrix", 10)
        self.sub("Security Testing Results")
        self.tbl(["Attack", "Result"], [
            ("Missing, malformed, forged, expired or replayed tokens on 74 protected operations", "Rejected with 401 on every route"),
            ("Pending, disabled and unverified accounts using the application", "Refused (403) on every application route"),
            ("Inspector B reading or changing inspector A's records", "Answered exactly like a record that does not exist"),
            ("Role escalation through profile fields, headers or the admin API", "Rejected (422 / 403)"),
            ("NoSQL operator objects and strings in queries, bodies and ids", "Rejected or matched literally; no widened queries"),
            ("HTML, SVG, PHP and executable files disguised as images; pixel-bomb image", "Rejected (415 / 413); server stayed healthy"),
            ("Wrong origin, missing security headers, public API docs in production mode", "No CORS for other origins; headers present; docs hidden"),
        ], [10.2, 5.8], "Table 5.3: Attack-style security tests", 10)
        self.sub("Issues Found and Resolved")
        self.tbl(["Issue", "Impact", "Resolution"], C.ISSUES, [3.8, 5.4, 6.8], "Table 5.4: Issues found and resolved during development", 10, bold_first=True)
        self.sub("Limitations")
        self.bullets(["The reference records and compliance rules are fictional demonstration data and must be replaced with official data before any real use.",
                      "Automated tests use a deterministic AI provider; live label reading depends on the provider and on photograph quality, and providers may be temporarily unavailable.",
                      "Free hosting tiers sleep after inactivity, so the first request can take up to about a minute."])

        # ---------------- chapter 6
        self.chapter(6, "CONCLUSION & FUTURE ENHANCEMENTS")
        self.section("6.1 Conclusion")
        P(C.CONCLUSION)
        self.section("6.2 Future Enhancements")
        for a, b in C.FUTURE:
            self.titled_bullet(a, b)

        # ---------------- appendix
        self.chapter(0, "APPENDIX (SOURCE / PSEUDO CODE)")
        for i, (title, src, rx, nl, note) in enumerate(C.CODE_SNIPPETS, 1):
            self.section(f"A.{i} {title}")
            self.code(f"Listing A.{i}", src, snippet(src, rx, nl), note)

        # ---------------- references and abbreviations
        self.chapter(0, "REFERENCES")
        for name, url in C.BIBLIOGRAPHY:
            p = self.doc.add_paragraph()
            p.paragraph_format.left_indent, p.paragraph_format.first_line_indent = Cm(0.8), Cm(-0.5)
            p.paragraph_format.space_after = Pt(5)
            add_runs(p, f"►  **{name}.** Available at: ", 11.5)
            r = p.add_run(url)
            set_font(r, 11, color=RGBColor(0x1F, 0x4E, 0x9E))
            r.font.underline = True
        self.chapter(0, "LIST OF ABBREVIATIONS")
        abbr = [("AI", "Artificial Intelligence"), ("API", "Application Programming Interface"), ("CI/CD", "Continuous Integration / Continuous Deployment"), ("CORS", "Cross-Origin Resource Sharing"),
                ("CSP", "Content Security Policy"), ("CSV", "Comma-Separated Values"), ("FSSAI", "Food Safety and Standards Authority of India"), ("GridFS", "MongoDB file storage specification"),
                ("HTTP / HTTPS", "HyperText Transfer Protocol (Secure)"), ("IDE", "Integrated Development Environment"), ("JSON", "JavaScript Object Notation"), ("JWT", "JSON Web Token"),
                ("LLM", "Large Language Model"), ("NoSQL", "Not Only SQL"), ("OCR", "Optical Character Recognition"), ("PDF", "Portable Document Format"), ("REST", "Representational State Transfer"),
                ("UI / UX", "User Interface / User Experience"), ("URL", "Uniform Resource Locator")]
        for a, b in abbr:
            p = self.doc.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.left_indent = Cm(0.8)
            add_runs(p, f"►  **{a}** – {b}", 11.5)
        self.P("AI Models and Services Used", 12.5, "l", True, before=12, after=3)
        for a, b in [("Gemini", "Google's generative AI model (primary label reader)"), ("NVIDIA", "Hosted multimodal model used as the fallback reader"), ("Firebase Auth", "Google sign-in and ID tokens"),
                     ("MongoDB Atlas", "Hosted database and file storage"), ("Render", "Cloud hosting of the API and the website")]:
            p = self.doc.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.left_indent = Cm(0.8)
            add_runs(p, f"►  **{a}** – {b}", 11.5)


FRONT = ["Certificate", "Declaration", "Acknowledgement", "Vision and Mission", "Program Outcomes (POs)", "Course Objectives and Course Outcomes", "Course Certifications",
         "Abstract", "System Features", "List of Tables", "List of Figures"]
FRONT_SEARCH = {"Certificate": "certificate", "Declaration": "declaration", "Acknowledgement": "acknowledgement", "Vision and Mission": "vision and mission",
                "Program Outcomes (POs)": "program outcomes (pos)", "Course Objectives and Course Outcomes": "course objectives", "Course Certifications": "course certifications",
                "Abstract": "abstract", "System Features": "system features", "List of Tables": "list of tables", "List of Figures": "list of figures"}
BANNER = "\u0000"


def build(known, figs, tables, toc_pages, path: pathlib.Path) -> Report2:
    r = Report2(toc_pages, figs, tables, known)
    d = r.doc
    s0 = d.sections[0]
    r.header(s0, True)
    r.footer_plain(s0, show=False)
    r.cover()
    s1 = d.add_section(WD_SECTION.NEW_PAGE)
    r.header(s1, True)
    r.footer_plain(s1, True)
    numbering(s1, "lowerRoman", 1)
    r.certificate()
    r.declaration()
    r.acknowledgement()
    r.vision()
    r.outcomes()
    r.course()
    r.certifications()
    r.abstract()
    r.features()
    r.toc_front(FRONT)
    r.lists()
    s2 = d.add_section(WD_SECTION.NEW_PAGE)
    r.header(s2, False)
    r.footer_body(s2)
    numbering(s2, "decimal", 1)
    r.body()
    path.parent.mkdir(parents=True, exist_ok=True)
    d.save(path)
    return r


def to_pdf(docx):
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(docx.parent), str(docx)], check=True, capture_output=True, timeout=300)
    return docx.with_suffix(".pdf")


def pages_of(pdf):
    out = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    return [" ".join(p.split()).lower() for p in out.split("\f")]


def find_pages(pdf, r):
    pages = pages_of(pdf)
    res = {}
    # front matter: page text starts with the heading (after the banner text); roman number = pdf index
    for disp, key in FRONT_SEARCH.items():
        for i, t in enumerate(pages[1:], 1):
            t2 = t.replace(BANNER, "", 1).strip()
            if t2.startswith(key) and "table of contents" not in t2[:30]:
                res[disp] = roman(i)
                break
    start = next(i for i, t in enumerate(pages) if t.startswith("chapter 1 introduction"))
    for lvl, disp, key in r.entries:
        for i in range(start, len(pages)):
            t = pages[i]
            if (key in t) if lvl == 2 else t.startswith(key) or t.replace("dept of cse-allied [", "", 1).startswith(key):
                res[disp] = i - start + 1
                break
    for cap in r.found_figs + r.found_tables:
        needle = " ".join(cap.split()).lower()[:70]
        for i in range(start, len(pages)):
            if needle in pages[i]:
                res[cap] = i - start + 1
                break
    return res, start, len(pages)


def roman(n):
    vals = [(10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    out = ""
    for v, sym in vals:
        while n >= v:
            out += sym
            n -= v
    return out


if __name__ == "__main__":
    make_crops()
    tmp = HERE / "_tmp"
    tmp.mkdir(exist_ok=True)
    r0 = build([], [], [], {}, tmp / f"{NAME}.docx")
    known, figs, tables = r0.entries, r0.found_figs, r0.found_tables
    r1 = build(known, figs, tables, {}, tmp / f"{NAME}.docx")
    pdf = to_pdf(tmp / f"{NAME}.docx")
    pages, start, total = find_pages(pdf, r1)
    missing = [e for e in [d for _, d, _ in known] + figs + tables if e not in pages]
    if missing:
        print("WARNING: no page found for:", missing, file=sys.stderr)
    final = OUTDIR / f"{NAME}.docx"
    build(known, figs, tables, pages, final)
    pdf2 = to_pdf(final)
    print("written", final, pdf2, "pages:", len(pages_of(pdf2)), "body starts at pdf page", start + 1)
