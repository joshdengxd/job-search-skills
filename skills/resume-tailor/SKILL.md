---
name: resume-tailor
description: Tailor a master resume to one analyzed job without adding anything not in the candidate's verified facts. Use after analyzing a job, or when user says "tailor resume for this job" or "/resume-tailor".
---

# Resume Tailor

Self-contained. Paths below are defaults; the project/user may override them.

## Inputs
- Master resume (single fact bank), e.g. `master-resume.md`.
- Optional: career profile / fact-corrections file (what the candidate did NOT do or must not claim).
- The job: JD text plus any prior fit analysis (e.g. from `jd-analyzer`).
- Variant if the project has several (fullstack | frontend | backend).

## Standard
Master is a fact bank, not a submission copy: do NOT paste it. Cut hard: most recent role <= 5 bullets of <= 2 lines; older roles 2-3; drop bullets that do not map to the JD (they stay in master). 1 full page, or 2 pages with page 2 >= 50% filled. Top third of page 1 must show target-role fit and the 2 strongest JD-relevant proofs. If `resume-auditor` is installed, its rubric is the stricter acceptance standard.

## Allowed
- Reorder sections and bullets, DROP low-relevance bullets, merge and shorten bullets, tighten wording.
- Mirror the JD's terminology ONLY where the facts already support it (e.g. did SSR with Next.js/Node -> "server-side rendering").
- Rewrite the summary to the target role, using only verified facts.

## Forbidden
- Adding skills, tools, metrics, titles, dates, employers or responsibilities not in the master. A JD requirement with no evidence goes in the changelog as **Missing**, never into the resume.
- Inflating seniority; changing job titles.
- Internal URLs, hostnames, tickets, code or other confidential material from former employers.

## Format rules
Single column, plain headings (Summary, Experience, Skills, Education), no tables/text boxes/icons/photos, standard dates, text-selectable PDF. Unknown numbers stay as visible `[CONFIRM: ...]` placeholders (they block delivery until answered).

## Output (default dir `./tailored/`, name `<company>-<role-slug>-<YYYY-MM-DD>`)
- `<name>.md`, `<name>-changelog.md` (each change -> source line in master; Missing items; open questions), `<name>-jd.txt` (JD text).
- Then, if installed and in this order: `claim-verifier` (fabrication check) -> export PDF with `resume-pdf` -> `ats-check` (fresh subagent, must PASS) -> `resume-auditor` (fresh subagent each round, must PASS). Without these skills, self-check against the rules above.
- For submission, copy the audited PDF to a per-company submit folder under a NEUTRAL filename `<Candidate-Name>-Resume.pdf` (project may set the folder; NEUTRAL filename: a company name in the file name tells the recruiter the resume was tailored for them / risks sending the wrong one; PDF metadata is already empty). Upload only from that folder.
- The user reviews and submits manually. Never submit anything.
