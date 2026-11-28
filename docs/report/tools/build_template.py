"""Mini-project report TEMPLATE (DOCX) for the class: same layout as the CRATE-SCAN report, with placeholders instead of project content.

  python3 build_template.py     # writes ../Mini_Project_Report_Template.docx (a PDF preview is built in tools/_tmp only)

Yellow highlight = something the student must replace. The table of contents, list of tables and list of figures are real Word fields:
Word asks to update them when the file is opened; afterwards right-click → Update Field (or press F9) refreshes them."""

from __future__ import annotations

import pathlib

from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

import build_report_v2 as V
from build_report import ASSETS, add_runs, field, set_font

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "Mini_Project_Report_Template.docx"
IMG = ASSETS / "template"

# ---- generic values (patched into the module-level names the shared front-matter methods use)
V.TITLE = "[[PROJECT TITLE]]"
V.SUBTITLE = "[[Project sub-title / tag-line]]"
V.FULL = "[[PROJECT TITLE – Project sub-title]]"
V.TEAM = [("[[Student Name 1]]", "[[Roll No. 1]]"), ("[[Student Name 2]]", "[[Roll No. 2]]"), ("[[Student Name 3]]", "[[Roll No. 3]]")]
V.YEAR = "[[Academic Year, e.g. 2026–2027]]"
V.GUIDE, V.GUIDE_DESIG = "[[Guide Name]]", "[[Designation]]"


def make_images() -> None:
    from PIL import Image, ImageDraw, ImageFont

    IMG.mkdir(parents=True, exist_ok=True)
    try:
        f1 = ImageFont.truetype("DejaVuSans-Bold.ttf", 64)
        f2 = ImageFont.truetype("DejaVuSans.ttf", 34)
    except OSError:
        f1 = f2 = ImageFont.load_default()
    specs = {"certificate_1": ("CERTIFICATE 1", "Replace this image with your certificate", (1600, 1076)),
             "certificate_2": ("CERTIFICATE 2", "Replace this image with your certificate", (1600, 1076)),
             "figure": ("FIGURE", "Replace with your diagram / screenshot", (1600, 900)),
             "screen": ("SCREENSHOT", "Replace with your screenshot", (1600, 900))}
    for name, (a, b, size) in specs.items():
        im = Image.new("RGB", size, "#EEF1E4")
        d = ImageDraw.Draw(im)
        d.rectangle([12, 12, size[0] - 12, size[1] - 12], outline="#7A8F57", width=6)
        for text, font, dy in ((a, f1, -50), (b, f2, 40)):
            w = d.textlength(text, font=font)
            d.text(((size[0] - w) / 2, size[1] / 2 + dy), text, fill="#3E5228", font=font)
        im.save(IMG / f"{name}.png")


def fld(p, instr, result, size=11):
    """Complex field with a visible placeholder result."""
    def fc(kind):
        r = p.add_run()
        e = OxmlElement("w:fldChar")
        e.set(qn("w:fldCharType"), kind)
        if kind == "begin":
            e.set(qn("w:dirty"), "true")
        r._element.append(e)
    fc("begin")
    r = p.add_run()
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = instr
    r._element.append(it)
    fc("separate")
    V.HL(p, result, size, italic=True)
    fc("end")


class Template(V.Report2):
    def __init__(self):
        super().__init__({}, [], [], [])
        st = self.doc.styles
        for name, size, align in (("Front Heading", 14, WD_ALIGN_PARAGRAPH.CENTER), ("Figure Caption", 11, WD_ALIGN_PARAGRAPH.CENTER), ("Table Caption", 11, WD_ALIGN_PARAGRAPH.CENTER)):
            s = st.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
            s.base_style = st["Normal"]
            s.font.name, s.font.size, s.font.bold = V.FONT, Pt(size), name == "Front Heading"
            s.paragraph_format.alignment = align
            s.paragraph_format.space_after = Pt(10 if name == "Front Heading" else 12)
            if name == "Front Heading":
                s.paragraph_format.keep_with_next = True
                s.element.get_or_add_pPr().append(self._outline(0))

    @staticmethod
    def _outline(level):
        e = OxmlElement("w:outlineLvl")
        e.set(qn("w:val"), str(level))
        return e

    # ---- helpers
    def front_page(self, title, new_page=True, size=14):
        if new_page:
            self.doc.add_page_break()
        self.doc.add_paragraph(title, style="Front Heading")

    def ph(self, text, after=6):
        return self.P(f"[[{text}]]", 12, after=after)

    def figure(self, caption, kind="figure", width=14.0):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True
        p.paragraph_format.space_after = Pt(4)
        p.add_run().add_picture(str(IMG / f"{kind}.png"), width=Cm(width))
        label, _, text = caption.replace("[[", "[").replace("]]", "]").partition(":")
        c = self.doc.add_paragraph(style="Figure Caption")
        set_font(c.add_run(label + ":"), 11, True)
        r = c.add_run(text)
        set_font(r, 11)
        r.font.highlight_color = V.WD_COLOR_INDEX.YELLOW

    def tab(self, caption, headers, rows, widths):
        self.table(headers, rows, widths, 10.5)
        label, _, text = caption.replace("[[", "[").replace("]]", "]").partition(":")
        c = self.doc.add_paragraph(style="Table Caption")
        set_font(c.add_run(label + ":"), 11, True)
        r = c.add_run(text)
        set_font(r, 11)
        r.font.highlight_color = V.WD_COLOR_INDEX.YELLOW

    # ---- instructions page (not part of the report)
    def readme(self):
        self.doc.add_paragraph("HOW TO USE THIS TEMPLATE  (delete this page before submitting)", style="Normal").runs[0].font.bold = True
        for t in ["**Yellow highlight = replace it.** Project title, names, roll numbers, guide, coordinators, academic year and every instruction in square brackets must be changed. "
                  "Select the yellow text and type over it; then remove the highlight (Home → Text Highlight Color → No Color).",
                  "**Pictures:** right-click a grey placeholder picture → Change Picture → From a File (certificates, diagrams and screenshots). Keep the figure caption below it and renumber it.",
                  "**Captions:** every figure caption uses the style “Figure Caption” and every table caption uses “Table Caption”. Copy an existing caption paragraph for a new one so it appears in the lists.",
                  "**Headings:** chapter titles use Heading 1 and section titles use Heading 2. Use these styles for new headings so they appear in the table of contents.",
                  "**Table of contents, list of tables, list of figures:** these are automatic. When Word asks “update fields?”, click Yes. After you edit the report, click inside each list, "
                  "right-click → Update Field → Update entire table (or press F9).",
                  "**Certificates:** one page per team member with two image slots (Certificate 1 and Certificate 2). Copy a page to add more students; delete a page if you have fewer.",
                  "**Team size:** the cover, certificate and declaration show three students. Delete the extra lines if your team has fewer.",
                  "**Program Outcomes, Course Objectives and Course Outcomes** are filled in for the current syllabus. Edit them only if your department changes them.",
                  "**Page numbers:** roman numerals for the front matter and 1, 2, 3… for the chapters are already set. Do not delete the section breaks.",
                  "**Do not copy sentences from other reports.** Write the content in your own words, and cite every source in the References chapter."]:
            self.P("●  " + t, 11.5, "j", after=6)

    # ---- front matter overrides
    def acknowledgement(self):
        self.front_page("ACKNOWLEDGEMENT")
        P = self.P
        P("We would like to express our sincere gratitude to everyone who supported and guided us during this mini project.", after=9)
        P("We are thankful to **Dr. Rajesh H. Kulkarni**, Professor and Head of the Department, Department of Computer Science and Engineering (Allied), and to our Principal, "
          "[[Principal Name]], MVSR Engineering College, for providing the opportunity and the facilities required to complete this project.", after=9)
        P("We sincerely thank **Dr. B. Janaiah**, Senior Assistant Professor and Associate Head of the CSIT Department, for the constant support and encouragement.", after=9)
        P("We are grateful to the Mini Project Coordinators, [[Coordinator 1]] and [[Coordinator 2]], for coordinating the project work and for the timely guidance and support at every step.", after=9)
        P("We express our heartfelt thanks to our Project Guide, [[Guide Name]], [[Designation]], for the valuable guidance, suggestions and encouragement at every stage of this project and in the preparation of this report.", after=9)
        P("[[Add any other person or organisation you wish to thank.]]", after=9)
        P("Finally, we thank our parents and friends for their encouragement and support throughout the work.", after=26)
        for n, r in V.TEAM:
            P(f"**{n}** ({r})", 12, "r", after=2)

    def outcomes(self):
        self.front_page("PROGRAM OUTCOMES (POs)")
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
            pf.tab_stops.add_tab_stop(Cm(1.6))
            set_font(p.add_run(f"{code}:\t{head}: "), 11, True)
            set_font(p.add_run(txt), 11)

    def course(self):
        self.front_page("COURSE OBJECTIVES AND COURSE OUTCOMES")
        self.P("Course Objectives:", 12.5, "l", True, after=4)
        self.numbered(["Develop an application in the relevant area of Computer Science and allied courses.", "Learn Contemporary tools and technologies.",
                       "Expose the students to industry practices and teamwork.", "Encourage students to work with innovative and entrepreneurial ideas.",
                       "Familiarize students with all the aspects of technical documentation."])
        self.P("Course Outcomes:", 12.5, "l", True, after=4, before=14)
        self.P("On completion of the course, students will be able to:", 12, after=4)
        self.numbered(["Evaluate different solutions based on economic and technical feasibility.", "Effectively plan a project and confidently perform all aspects of SDLC.",
                       "Design a model to address the proposed problem.", "Adapt to contemporary technologies.",
                       "Demonstrate the work done in the project through presentation and documentation."])

    def certifications(self):
        for i in range(3):
            self.doc.add_page_break()
            if i == 0:
                self.doc.add_paragraph("COURSE CERTIFICATIONS", style="Front Heading")
            p = self.doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(4)
            V.HL(p, f"Certificates of [Student Name {i + 1}]", 11.5, True)
            for n in (1, 2):
                q = self.doc.add_paragraph()
                q.alignment = WD_ALIGN_PARAGRAPH.CENTER
                q.paragraph_format.space_after = Pt(6)
                q.add_run().add_picture(str(IMG / f"certificate_{n}.png"), height=Cm(8.2))

    def abstract(self):
        self.front_page("ABSTRACT")
        self.ph("Write the abstract in 200–300 words, in 3 short paragraphs: (1) the problem and why it matters; (2) what you built and how – the main technologies; (3) the results and what the project achieves.")
        self.ph("Do not use first person (“I”, “we”) and do not include references or figures in the abstract.")

    def features(self):
        self.front_page("SYSTEM FEATURES")
        for i in (1, 2, 3, 4, 5):
            self.P(f"**{i}. [[Feature name]]**", 12, "l", after=1, keep=True)
            self.ph("Describe the feature in one or two sentences: what the user can do and what the system does in response.", 8)
        self.ph("Add or delete features as needed (usually 8–15).")

    def toc_lists(self):
        for title, instr, hint in (("TABLE OF CONTENTS", 'TOC \\o "1-2" \\u \\h \\z', "Right-click here → Update Field → Update entire table, to build the table of contents."),
                                   ("LIST OF TABLES", 'TOC \\h \\z \\t "Table Caption,1"', "Right-click here → Update Field to build the list of tables."),
                                   ("LIST OF FIGURES", 'TOC \\h \\z \\t "Figure Caption,1"', "Right-click here → Update Field to build the list of figures.")):
            self.doc.add_page_break() if title != "TABLE OF CONTENTS" else None
            self.P(title, 14, "c", True, after=10, keep=True)
            p = self.doc.add_paragraph()
            fld(p, instr, hint)

    # ---- body
    def body(self):
        P, ph = self.P, self.ph
        self.chapter(1, "INTRODUCTION")
        self.section("1.1 Detailed Problem Statement")
        ph("Describe the problem: who faces it, how it shows up today, and why it needs a solution (1–2 pages).")
        self.section("1.2 Analysis of Existing Systems")
        ph("Describe the existing solutions or methods and list their drawbacks. Use short bullets or a comparison table.")
        self.section("1.3 Proposed System")
        ph("Explain your solution in 2–3 paragraphs and list its key features.")
        self.section("1.4 Comprehensive Project Scope")
        ph("State what the project covers, who will use it, and what it deliberately does not cover.")
        self.section("1.5 Project Objectives")
        self.bullets(["[[Objective 1]]", "[[Objective 2]]", "[[Objective 3]]"])

        self.chapter(2, "SYSTEM REQUIREMENT SPECIFICATIONS")
        self.section("2.1 Software Requirements")
        self.tab("Table 2.1: [[Software requirements]]", ["Area", "Technology / Tool (with version)", "Purpose"],
                 [("[[Operating system]]", "[[e.g. Windows 11]]", "[[…]]"), ("[[Front-end]]", "[[…]]", "[[…]]"), ("[[Back-end]]", "[[…]]", "[[…]]"), ("[[Database]]", "[[…]]", "[[…]]"), ("[[Tools]]", "[[…]]", "[[…]]")], [3.4, 6.2, 6.4])
        self.section("2.2 Hardware Requirements")
        self.tab("Table 2.2: [[Hardware requirements]]", ["Item", "Specification"],
                 [("[[Processor]]", "[[…]]"), ("[[Memory (RAM)]]", "[[…]]"), ("[[Storage]]", "[[…]]"), ("[[Network]]", "[[…]]")], [5.0, 11.0])
        self.section("2.3 Detailed System Architecture")
        ph("Explain the architecture (client, server, database, external services) in one or two paragraphs and refer to the figure.")
        self.figure("Figure 2.1: [[System architecture of the project]]")

        self.chapter(3, "DESIGN & IMPLEMENTATION")
        self.section("3.1 Features List")
        self.bullets(["**[[Feature 1]]:** [[one-line description]]", "**[[Feature 2]]:** [[one-line description]]", "**[[Feature 3]]:** [[one-line description]]"])
        self.section("3.2 Modules Description")
        self.tab("Table 3.1: [[Modules of the project]]", ["Module", "Description"], [("[[Module 1]]", "[[What it does and which data it uses]]"), ("[[Module 2]]", "[[…]]"), ("[[Module 3]]", "[[…]]")], [4.4, 11.6])
        self.section("3.3 UML Diagrams")
        self.sub("Use Case Diagram")
        self.figure("Figure 3.1: [[Use case diagram]]")
        self.sub("Activity Diagram")
        self.figure("Figure 3.2: [[Activity diagram]]")
        self.sub("Sequence / Class / ER Diagram")
        self.figure("Figure 3.3: [[Sequence, class or ER diagram]]")
        self.section("3.4 Environmental Setup")
        ph("List the steps to set up the development environment (install tools, get the code, install dependencies, run the project), with the exact commands and a screenshot where useful.")
        self.figure("Figure 3.4: [[Screenshot of a setup step]]", "screen", 12.0)
        self.section("3.5 Implementation & Methodology Steps")
        self.numbered(["[[Requirement analysis – what you did]]", "[[Design – diagrams and decisions]]", "[[Development – how the modules were built]]", "[[Testing – how it was checked]]", "[[Deployment – how it is delivered]]"])

        self.chapter(4, "DETAILED PAGE FEATURES & CLOSE-UPS")
        self.section("4.1 Home Page / Main Screen Breakdown")
        ph("Show the main screen and explain each part of it (menu, buttons, areas).")
        self.figure("Figure 4.1: [[Main screen]]", "screen")
        self.section("4.2 Close-up Visuals: [Component name]")
        self.figure("Figure 4.2: [[Close-up of a component]]", "screen", 9.0)
        ph("Explain what the component does.")
        self.section("4.3 Detailed Button Mechanics & Core Functions")
        self.tab("Table 4.1: [[Main controls and their behaviour]]", ["Control", "What it does"], [("[[Button / control]]", "[[Behaviour]]"), ("[[Button / control]]", "[[Behaviour]]")], [5.0, 11.0])

        self.chapter(5, "RESULTS & DISCUSSION")
        for i in (1, 2, 3):
            self.section(f"5.{i} [Screen / feature name]")
            self.P("**Test Focus:**", after=2, keep=True, align="l")
            self.bullets(["[[What was tested]]"], keep=True)
            self.P("**Result:**", after=2, before=6, keep=True, align="l")
            self.ph("Describe what the screenshot shows and what the test proved.", 8)
            self.figure(f"Figure 5.{i}: [[Screenshot caption]]", "screen")
        self.section("5.4 Validation & Testing")
        self.tab("Table 5.1: [[System test matrix]]", ["TC", "Scenario", "Expected result", "Status"],
                 [("TC-1", "[[…]]", "[[…]]", "[[PASS / FAIL]]"), ("TC-2", "[[…]]", "[[…]]", "[[PASS / FAIL]]"), ("TC-3", "[[…]]", "[[…]]", "[[PASS / FAIL]]")], [1.4, 5.6, 7.2, 1.8])
        self.section("5.5 Limitations")
        self.bullets(["[[Limitation 1]]", "[[Limitation 2]]"])

        self.chapter(6, "CONCLUSION & FUTURE ENHANCEMENTS")
        self.section("6.1 Conclusion")
        ph("Summarise what was achieved against the objectives, in 1–2 paragraphs.")
        self.section("6.2 Future Enhancements")
        self.bullets(["[[Enhancement 1]]", "[[Enhancement 2]]", "[[Enhancement 3]]"])

        self.chapter(0, "APPENDIX (SOURCE / PSEUDO CODE)")
        self.section("A.1 [Name of the code listing]")
        ph("Paste the important code or pseudo code here in Courier New, size 9. Add a one-line note on what it does.")

        self.chapter(0, "REFERENCES")
        for i in (1, 2, 3):
            self.P("►  [[Author / Organisation. Title. Year. Available at: URL]]", 11.5, "l", after=5)
        self.chapter(0, "LIST OF ABBREVIATIONS")
        for a in ("[[ABBR – Full form]]", "[[ABBR – Full form]]", "[[ABBR – Full form]]"):
            self.P("►  " + a, 11.5, "l", after=2)


def pgnum(section, fmt, start=None):
    sect = section._sectPr
    for e in sect.findall(qn("w:pgNumType")):
        sect.remove(e)
    pg = OxmlElement("w:pgNumType")
    pg.set(qn("w:fmt"), fmt)
    if start is not None:
        pg.set(qn("w:start"), str(start))
    sect.append(pg)


def build(path: pathlib.Path) -> None:
    make_images()
    r = Template()
    d = r.doc
    s0 = d.sections[0]
    r.header(s0, False)
    r.footer_plain(s0, False)
    r.readme()
    s1 = d.add_section(WD_SECTION.NEW_PAGE)
    r.header(s1, True)
    r.footer_plain(s1, False)
    r.cover()
    s2 = d.add_section(WD_SECTION.NEW_PAGE)
    r.header(s2, True)
    r.footer_plain(s2, True)
    pgnum(s2, "lowerRoman", 1)
    r.certificate()
    r.declaration()
    r.acknowledgement()
    r.vision()
    r.outcomes()
    r.course()
    r.certifications()
    r.abstract()
    r.features()
    s3 = d.add_section(WD_SECTION.NEW_PAGE)
    r.header(s3, False)
    r.footer_plain(s3, True)
    pgnum(s3, "lowerRoman")
    r.toc_lists()
    s4 = d.add_section(WD_SECTION.NEW_PAGE)
    r.header(s4, False)
    r.footer_body(s4)
    pgnum(s4, "decimal", 1)
    r.body()
    st = d.settings.element
    uf = OxmlElement("w:updateFields")
    uf.set(qn("w:val"), "true")
    st.append(uf)
    d.save(path)


if __name__ == "__main__":
    build(OUT)
    tmp = HERE / "_tmp"
    tmp.mkdir(exist_ok=True)
    import shutil

    shutil.copy(OUT, tmp / OUT.name)
    pdf = V.to_pdf(tmp / OUT.name)
    print("written", OUT, "preview pages:", len(V.pages_of(pdf)))
