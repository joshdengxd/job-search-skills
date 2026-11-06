---
name: application-tracker
description: Maintain local job-tracking CSVs (opportunities + applications). Use when user says "track this job", "update application status", "what's pending", "follow-ups", or after analyzing a job.
---

# Application Tracker

Self-contained. `<skill-dir>` = this folder. No scripts: edit the CSVs directly (keep the header row and column order).

## Files (default dir `./jobs/`)
- `opportunities.csv`: postings found by searching or scanning. Header template: `<skill-dir>/references/opportunities.template.csv`.
- `applications.csv`: jobs the user is pursuing. Header template: `<skill-dir>/references/applications.template.csv`.
If a file is missing, create it from the template header (UTF-8 with BOM so Excel opens it cleanly).

## Status values
`considering` -> `analyzed` -> `tailored` -> `ready-for-user` -> `submitted` -> `recruiter-screen` -> `interview` -> `offer` | `rejected` | `withdrawn` | `closed`.

## Rules
- Local CSV edits only. No submitting, scraping, logins, or sending emails.
- `human_approved_submit` = Y only when the user said so in chat for that specific job. `submitted` is set only after the user confirms they submitted.
- Gate-failed jobs are not added to applications; they stay in opportunities with a note.
- Dates are ISO. Re-check that a posting is still open when its row is more than 14 days old.
- On request: list follow-ups due, counts per stage, and conversion (submitted -> screen -> interview -> offer) once there is data. Keep summaries short.
