---
name: ats-check
description: Local ATS-readiness gate for a resume PDF - 3-parser text extraction, format/density checks, JD keyword coverage, 0-100 heuristic score (pass >= 90). Runs in a separate fresh subagent. Use after tailoring a resume or on any resume PDF change, or on "/ats-check".
---

# ATS Check (separate-subagent gate)

Self-contained. `<skill-dir>` = this folder. Needs Python 3.10+ and `pip install -r <skill-dir>/scripts/requirements.txt` (pymupdf, pdfplumber, pypdfium2; PyMuPDF is AGPL-3.0). Local only: no network, no LLM, no upload of the resume.

The score is a heuristic of verifiable checks, NOT a real ATS score. Fix failing checks; never keyword-stuff or add terms the candidate cannot defend in an interview.

## Inputs
- `RESUME.pdf` (required, text-selectable PDF).
- `--jd JD.txt` (optional, enables keyword checks).
- `--master MASTER.md` (optional but recommended): the candidate's full fact-bank resume. With it, JD terms missing from the resume split into "in master: add if true + relevant" vs "Missing: never add". Without it, all uncovered terms are only "not in resume" and the keyword score is less meaningful.
- `--terms terms.json` (optional): custom vocabulary. Default `<skill-dir>/scripts/terms.json` (software-engineering terms; edit/extend for other fields).

## Run
```bash
python <skill-dir>/scripts/ats_check.py RESUME.pdf --jd JD.txt --master MASTER.md --save
```
`--save` writes `./ats-reports/<pdf-stem>-ats.json` and prints the score delta vs the previous run. Exit code 0 PASS, 1 FIX, 2 FAIL.

## Gate
PASS = score >= 90 AND no hard fail (unparseable text, garbage chars, missing standard headings, images/tables/columns, placeholders like `[CONFIRM]`, missing contact). FIX/FAIL -> fix, rebuild PDF, re-run. Max 2 fix rounds, then ask the user.

## Run it in a separate fresh subagent (orchestrator steps)
1. Make sure the PDF, JD text and (if any) master file exist at stable paths.
2. Launch a NEW subagent (general-purpose, NOT a fork, fresh each round). Prompt is self-contained: read-only (no edits, no network, nothing sent), run the command above, then report: score, verdict, every WARN/FAIL with the script message; terms "in master, NOT in resume" (is adding TRUE + relevant per master?); "Missing" terms (confirm none appear in the resume); any resume keyword NOT supported by master (fabrication flag); top 3 fixes by impact; sanity-check what the script cannot (keyword stuffing, unnatural phrasing). <= 300 words. Do not share the author's reasoning or an expected verdict.
3. Save the report next to the resume (e.g. `<name>-ats-roundN.md`).
4. Apply fixes (existing facts only), rebuild PDF, NEW subagent for the next round.
5. Hand over only on PASS. Never submit anything for the user.

## Checks
- P1-P4 parse: extractable; ligature/garbage chars (re-render PDF if ligatures); Summary/Experience/Skills/Education headings; token-order agreement across parsers (low = columns/odd layout).
- F1-F8 format: images/tables/columns; contact not in header/footer; 1 page filled >= 80% or 2 pages with page 2 >= 50%; density (latest role <= 5 bullets, older roles <= 3, bullets <= ~32 words, max 1 longer); min font >= 8.5pt; no placeholders; standard dates; email+phone.
- K1 keywords (needs `--jd`): score counts only terms the candidate could truthfully add.
- "Unclassified JD tokens": tech-looking words outside the vocabulary; review by hand, not scored.

## Limits
Density checks parse bullet glyphs and date lines from the PDF text; unusual layouts yield WARN, not PASS. Vocabulary is software-oriented.
