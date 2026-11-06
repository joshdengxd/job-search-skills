---
name: resume-auditor
description: Independent fresh-context audit of a tailored resume (truthfulness, completeness, interview-getting power) against a bundled rubric. Use after tailoring and on ANY resume/LinkedIn text change, or on "/resume-auditor".
---

# Resume Auditor (fresh-context cross-check)

Self-contained. `<skill-dir>` = this folder. Rubric: `<skill-dir>/references/acceptance-criteria.md` (hard fails A1-A5, scored B1-B12). The agent that wrote a resume is biased toward it, so the audit MUST be done by a NEW subagent with fresh context each round.

## Inputs (paths set by the caller / project config)
- JD text, tailored resume `.md`, exported PDF (optional), tailoring changelog (optional).
- Master resume (fact bank) and optional fact-corrections file (things the candidate must NOT claim).
- Optional helpers if installed: `claim-verifier` (mechanical diff vs master), `ats-check` (parse/format/keyword gate, separate subagent).

## Steps
1. Put inputs at stable paths.
2. Launch a NEW subagent (general-purpose, NOT fork; fresh every round). Self-contained prompt, read-only (no edits, no network, nothing sent), no tailor reasoning, no verdict hint. Give it:
   - the rubric path and input paths;
   - task: audit independently against every criterion; verify facts by reading master/corrections; check PDF page count and fill (PyMuPDF) if a PDF exists; run `claim-verifier` if present; if an ats-check report exists, read it and judge only what the script cannot (B1, B4, B5, B8-B12) and flag any keyword the master does not support;
   - output: per-criterion PASS/FIX/FAIL with quoted evidence; top 3 fixes ranked by interview impact; biggest rejection reason; final verdict PASS/FAIL; <= 500 words.
3. Save the report next to the resume (`<name>-audit-roundN.md`).
4. Apply fixes (existing facts only), re-run the fact check, launch a NEW auditor (round N+1). Max 2 fix rounds, then ask the user.
5. Hand over only on PASS. Never submit anything; the user submits manually.
