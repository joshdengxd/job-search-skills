# job-search-skills

Small, self-contained agent skills (Claude Code / Codex) for an evidence-based job search. Each folder in `skills/` works alone: `SKILL.md` + its own scripts/data. No personal data; you supply your own profile and rules.

| Skill | Purpose | Needs |
|---|---|---|
| jd-analyzer | Gate a posting vs your hard requirements + evidence map | stdlib |
| resume-tailor | Tailor a master resume to one job, existing facts only | - |
| resume-pdf | Markdown -> ATS-safe 1-page PDF | pymupdf |
| claim-verifier | Diff tailored resume vs master to catch fabrication | stdlib |
| ats-check | Local parse/format/keyword gate (heuristic, not a real ATS score) | pymupdf, pdfplumber, pypdfium2 |
| resume-auditor | Fresh-subagent audit against a bundled rubric | - |
| application-tracker | Plain CSV tracker (templates bundled) | - |
| job-scan | Scheduled scan of public ATS boards, notify on strong fits | stdlib |

## Workflow (per job)
1. `jd-analyzer`: hard-requirement gates. Any failed gate = stop.
2. `resume-tailor`: tailored resume + changelog (verified facts only).
3. `claim-verifier`: must pass.
4. `resume-pdf` -> `ats-check` -> `resume-auditor`: fix failures, max 2 rounds.
5. `application-tracker`: log. You review and submit manually.

## Principles
- Never fabricate achievements, metrics, titles, dates.
- No auto-submitting applications; no scraping or mass messaging.
- Skills take paths as arguments; your private files stay in your own project.

## Install
Copy a folder from `skills/` into `.claude/skills/` (Claude Code) or `~/.codex/skills/` (Codex).

Run `python tools/lint_skills.py` before publishing changes (flags project paths and personal data).

## License
MIT (see LICENSE). This repo ships no PyMuPDF code. `resume-pdf` and `ats-check` import PyMuPDF (AGPL-3.0) at runtime; it is installed separately and its license applies to your use of it.
