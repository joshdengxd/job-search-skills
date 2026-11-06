---
name: form-auditor
description: Independent fresh-context audit of a FILLED but NOT YET SUBMITTED online application form against the candidate's verified answers. Use after filling each form/page and before any submit, or on "/form-auditor".
---

# Form Auditor

Purpose: catch wrong or unsupported answers (wrong dropdown option, wrong yes/no, fabricated fact, missing required field, wrong file) before a form is submitted. The agent that filled the form must NOT audit it.

## Rules
- Run as a NEW subagent with fresh context every time (never reuse one, never share the filler's reasoning). Give it only: the browser tab id, the job URL, the answers sheet path, the resume file path, and these instructions.
- The auditor is READ-ONLY on the page: read text/accessibility tree, take screenshots, scroll. It must NOT click Submit/Next, change any field, open file pickers, log in, or navigate away.
- Audit every page/section of the form; scroll the whole form (long forms hide fields below the fold). Dropdowns that show only the selected value: verify the selected text, not the typed text.

## Inputs the caller passes
- `answers sheet`: the project's standard truthful answers (identity, contact, work authorization, sponsorship, location, pay rule, self-ID, consent, past employers, skills yes/no).
- `profile facts`: master resume / career profile for any factual question (years of experience, tools, degrees).
- `resume file`: the file that should be attached (name must match; neutral filename if the project requires one).
- `job file`: JD text + posting URL (to check location/remote/pay-related fields).

## Audit checklist (each field -> PASS / FAIL / UNSURE with evidence)
1. Identity/contact: names, email, phone, city/region, LinkedIn URL match the sheet exactly.
2. Attachments: correct resume attached (filename), no stray/old files, cover letter only if approved.
3. Yes/No and dropdowns: each answer is truthful per the sheet/profile (work authorization, sponsorship, relocation, remote, prior employment, skills such as "2+ years of X": must match profile, never inflated).
4. Substring traps: option text matches the intended option (e.g. "Man" vs "Woman", "don't wish to answer" vs "No, I don't have..."); the sheet's self-ID rules are followed; unknown self-ID items use the decline option, never a guess.
5. Free text: only text the user approved; no AI-sounding filler; no fabricated claims; matches the project's voice guide.
6. Pay: follows the project's pay rule (e.g. midpoint of posted range) and currency.
7. Required fields: none empty; no validation errors visible; consent/agreement boxes only ticked if the user approved ticking them.
8. Hidden/extra items: unexpected fields added since the form was read, conditional fields that appeared after answers.
9. Anything that looks wrong but is not covered by the sheet = UNSURE -> report to the user, do not guess.

## Output (concise)
`VERDICT: PASS | FAIL` then a table: field | expected | actual | status. List FAIL/UNSURE items first with the fix to apply. Do not include praise.

## Caller loop
Fill form -> spawn NEW auditor -> if FAIL/UNSURE: fix (or ask the user for UNSURE items), then spawn another NEW auditor -> repeat until PASS (max 3 rounds, then ask the user) -> only then submit, and only if the user asked to submit this job. Log the audit result in the tracker notes.
