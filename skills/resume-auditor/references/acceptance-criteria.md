# Resume acceptance criteria (single standard for tailoring + auditing)

Goal: the resume most likely to get an interview for ONE target job, while staying 100% true. The master resume (full fact bank) is NOT the submission copy. These are heuristics from public hiring guidance, not guarantees.

Rating per criterion: **PASS / FIX / FAIL**. Verdict PASS = zero hard fails and zero FAIL. FIX items must be fixed, then re-audited by a NEW fresh auditor (max 2 rounds, then escalate to the user).

## A. Hard fails (any one = FAIL, blocks delivery)
- A1 Fabrication or change: new number/tool/title/employer/date/scope vs the master resume.
- A2 Inflated scope (e.g. "led" for "participated"), or contradicts the candidate's fact-corrections file (things the candidate said they did NOT do or must not claim), if one exists.
- A3 `[ ]` / `[CONFIRM]` placeholders, internal URLs/hostnames/tickets/code from confidential sources.
- A4 JD must-have with no evidence presented as a skill (must be listed as Missing in the changelog instead).
- A5 Parse-risk format in the PDF: columns, tables, icons, text boxes, image text, header/footer contact.

## B. Scored criteria
1. **10-second scan** (top third of page 1: name, title line, summary, first bullets): shows target-role fit, years, and the 2 strongest JD-relevant proof points.
2. **Density**: most recent role <= 5 bullets; each bullet <= 2 lines (~30 words), at most ONE flagship bullet up to 3 lines; roles older than 3 yrs <= 2-3 bullets; no sub-bullets deeper than one level.
3. **Length**: exactly 1 full page, OR 2 pages with page 2 >= 50% filled. Never ~1.2-1.5 pages.
4. **Bullet quality**: starts with a strong verb; one idea per bullet; outcome + measure + how where a verified number exists (X-Y-Z); no tool-list laundry; no sentence the candidate can't defend in an interview.
5. **Relevance**: >= 70% of bullets in the top two roles map to JD must-haves/nice-to-haves; irrelevant bullets cut (they stay in master). Order by JD relevance.
6. **Keywords**: JD must-have terms appear verbatim where TRUE (summary/skills/bullets); Missing items NOT faked.
7. **Numbers**: only candidate-verified; estimates worded "about"; baseline given when claiming improvement.
8. **Summary**: 2-3 lines, role + years + top 2-3 JD-relevant proofs; no buzzword filler; no claims beyond bullets.
9. **Skills**: grouped, ordered by JD relevance, <= 6 lines, nothing unverified.
10. **Credibility/consistency**: titles/dates/employers identical to master and public profile; seniority honest; no internal contradictions; tenure pattern not highlighted.
11. **Differentiation**: specific nouns and real numbers, not generic LLM voice.
12. **Skeptic test**: argue BOTH "would a hiring manager at this company invite this person?" and "why not?", name the single biggest reason to reject, and whether the resume can fix it truthfully.

## B+. Automated pre-check
If the `ats-check` skill is available, run it first in a separate fresh subagent (gate: score >= 90, no hard fail). It covers A3/A5, B2, B3, B6 deterministically. The auditor then judges B1, B4, B5, B8-B12.

## C. Process gate
Tailor -> fact check (`claim-verifier` if available) -> `ats-check` (if available) -> fresh-context `resume-auditor` (new subagent each round, never reused, never told the tailor's reasoning) -> fix -> re-audit until PASS. Only then hand to the user. The user submits manually.
