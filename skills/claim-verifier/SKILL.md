---
name: claim-verifier
description: Check a tailored resume or LinkedIn text against the master resume for fabricated or changed claims (new numbers, tools, titles, employers, dates). Use after tailoring, before any resume goes to the user, or on "/claim-verifier".
---

# Claim Verifier

Self-contained. `<skill-dir>` = this folder. Python 3.10+ stdlib only, no network.

## Step 1: mechanical diff
```bash
python <skill-dir>/verify.py <master.md> <tailored.md>
```
Lists numbers and tool-like/capitalized tokens that appear in the tailored text but not in the master. Exit code 1 if any. Both paths are required arguments (the master is the candidate's full fact-bank resume).

## Step 2: manual judgment
For each flagged item decide:
- Harmless (common word, or JD-term reword of an existing fact): note why.
- Unsupported: remove it, or ask the user; record as Missing.

Also check: titles, dates and employers unchanged; no confidential internal details; no inflated scope ("led" vs "contributed"); `[CONFIRM: ...]` placeholders still visible.

## Output
Pass/Fail report: flagged items, decision per item, final verdict. Fail blocks delivery.
