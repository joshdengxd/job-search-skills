---
name: job-search-workflow
description: Orchestrate the per-job pipeline (analyze, tailor, verify, ATS check, audit, form audit, track) using the sibling job-search skills, with fresh-subagent quality gates and human approval before any submit. Use when the user says "run the workflow for this job", "apply pipeline", or "/job-search-workflow".
---

# Job Search Workflow (orchestrator)

Self-contained playbook. `<skill-dir>` = this folder. It calls sibling skills by name if installed; it holds no data and no personal paths. The caller passes file paths (requirements file, master resume, answers sheet, output dirs).

Design rationale and diagram: `<skill-dir>/references/pipeline.md`.

## Steps (per job)
1. `jd-analyzer`: gate the posting vs the hard requirements. Any Ineligible gate = STOP, log, do nothing else.
2. `resume-tailor`: tailored resume + changelog, existing facts only.
3. `claim-verifier`: mechanical fabrication diff vs master. Must pass.
4. `resume-pdf` -> `ats-check`: run in a NEW fresh subagent. PASS = score >= 90 and no hard fail. Max 2 fix rounds, new subagent each round. Fix real failures only; never keyword-stuff.
5. `resume-auditor`: NEW fresh-context subagent audits against the bundled rubric. Required after ANY resume/profile edit. Max 2 fix rounds, new auditor each round.
6. Fill the application form (human-paced browsing, drafts of free-text answers shown to the user first).
7. `form-auditor` (if installed): after filling EACH page and BEFORE any submit, a NEW fresh subagent audits the live form read-only against the answers sheet + master. Any FAIL/UNSURE -> fix, new auditor, repeat (max 3 rounds, then ask the user).
8. `application-tracker`: log status.
9. STOP. The user reviews and submits. Mark "approved/submitted" only on the user's word.

## Rules
- The agent that produced an artifact never audits it. Every gate is a new subagent with no producer reasoning and no verdict hint.
- Gates are objective where possible (scripts) and rubric-based where not (auditors). Rounds are capped, then a human decides.
- Label every claim Verified / User estimate / Unverified / Missing. Missing = never added.
- No auto-submit, no scraping, no mass messaging. Any outward-facing action needs explicit user approval.
- Skills stay generic; project paths and rules live in the caller's own config.
