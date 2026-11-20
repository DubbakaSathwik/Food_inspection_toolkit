# CRATE-SCAN project report and presentation

| File | What |
|------|------|
| `CRATE-SCAN_Project_Report.docx` / `.pdf` | Mini-project report (51 pages) following the reference report's structure |
| `CRATE-SCAN_Presentation.pptx` / `.pdf` | Designed 25-slide deck following the reference presentation's structure |

## Fill in your details (yellow highlighted `[…]` text)
Student names and roll numbers, guide name and designation, project coordinators, academic year. Edit them in `tools/report_content.py`
(`TEAM`, `GUIDE`, `COORDINATORS`, `YEAR`, `HOD`, `PRINCIPAL`) and regenerate, or edit the highlighted text directly in the Word/PowerPoint files.

## Regenerate
```bash
python3 tools/make_diagrams.py && node tools/render_diagrams.cjs   # diagrams (only if you change them)
python3 tools/build_report.py                                       # report .docx + .pdf
python3 tools/build_deck.py                                         # slides .pptx + .pdf
```
Needs: python-docx, python-pptx, Pillow, LibreOffice (`soffice`), poppler (`pdftotext`), and Playwright (diagrams). Screenshots in `assets/screens/`
come from `tools/capture_screens.spec.ts` (run against the local stack with demo data).

All figures, test counts and code excerpts come from the project itself (test numbers: 75 backend, 9 unit, 44 browser, 49 attack-style).
The reference records and rules shown in screenshots are fictional demonstration data.
