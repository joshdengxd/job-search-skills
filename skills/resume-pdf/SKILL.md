---
name: resume-pdf
description: Render a resume markdown file to a clean single-column, text-selectable, ATS-parseable PDF (1-page fit or compact). Use when exporting or rebuilding a resume PDF, or on "/resume-pdf".
---

# Resume PDF

Self-contained. `<skill-dir>` = this folder. Needs Python 3.10+ and `pip install pymupdf` (AGPL-3.0). Local only.

```bash
python <skill-dir>/scripts/build_pdf.py INPUT.md OUTPUT.pdf [compact|fit]
```
- `fit` shrinks the font (9.6 -> 8.8pt) until the resume fits ONE page; `compact` uses tighter spacing; default is normal.
- Built-in font only. Ligatures are suppressed (an empty span after `f`), because ligature glyphs (fi/fl) break keyword extraction in ATS parsers; system TTFs were tested and corrupted hyphens/spaces in the text layer.
- Single dark-blue accent (name + section headings). No tables, columns, icons or images.
- Stops at the first `## Maintainer notes` / `## Editor notes` heading and drops the banner above the first `---`, so notes in the markdown never reach the PDF.

## Markdown conventions
`# Name`, contact line, `## Section` headings, `**Role** — Company · dates` role lines, `- ` bullets, `**bold**`/`*italic*` inline.

## After building
Check the page count and run `ats-check` if installed. Open the PDF and eyeball it once.
