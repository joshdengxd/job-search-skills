---
name: jd-analyzer
description: Analyze one job posting against the user's hard requirements and verified career facts. Use when the user pastes a JD/URL, asks "is this job a fit", "analyze this job", or "/jd-analyzer". Outputs gate table + evidence map, never a numeric match score.
---

# JD Analyzer

Self-contained. `<skill-dir>` = this folder. Python 3.10+ stdlib only for the fetch helper. Paths below are defaults; the project may override them.

## Inputs
- Requirements file (default `./preferences.md`; template: `<skill-dir>/references/requirements-template.md`). It defines the hard gates. If missing, ask the user to fill the template before analyzing.
- Master resume / career profile (default `./master-resume.md`, optional `./career-profile.md`): the only source of candidate facts.
- Posting text and/or official URL. If only a URL, fetch it. Record `date_checked` (today). Prefer the official career page over aggregators.

## Fetch helper
`python <skill-dir>/scripts/fetch_jd.py` pulls JD text (+ pay ranges, + application-form notes) for Greenhouse / Ashby / Lever postings via their public APIs; see its docstring for the input format. Otherwise use WebFetch or the browser.

## Application form check (mandatory)
Read the application form, not just the posting: Greenhouse `?questions=true` (fetch_jd.py prints 'APPLICATION FORM NOTES'), Ashby/Lever `<url>/application`. Look for province/state hiring restrictions, sponsorship, location limits, knockout questions. A region list that excludes the candidate's region = location gate Ineligible even if the posting says "Remote - <country>".

## Company brief
Every analysis and every recommendation message must start with a short brief: what the company does, who its customers are, the business model (how it makes money), size/stage/funding, headcount, trend (layoffs/growth). Cite sources and label third-party/aggregator numbers as unverified. Keep it to 4-6 lines.

## Output
Write `./analyses/<company>-<role-slug>-<YYYY-MM-DD>.md`:
1. **Header**: company, title, seniority, URL, date checked. Then the **Company brief** (see above).
2. **Hard-requirement gates**, one per line of the requirements file, each `Eligible | Ineligible | Unverified` + quote/evidence. Unknown = Unverified, never Eligible.
3. **Requirements split**: must-have vs nice-to-have, as written in the posting.
4. **Evidence map**: each requirement -> candidate fact with label Verified / User estimate / Missing. Missing stays Missing; never infer skills.
5. **Gaps + risks** (e.g. unused stack, short tenures).
6. **Recommended resume variant** and what to emphasize, using existing facts only.
7. **Questions** for the user and for the recruiter.

## Rules
- Any Ineligible gate => verdict "Do not pursue" regardless of fit. Unverified gates => list as action items.
- NO numeric match score, no "ATS score".
- No fabricated facts about the company; label unverified claims.
- If `application-tracker` is installed, add/update the row there.
