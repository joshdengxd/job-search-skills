# Pipeline design

```
posting
  |
  v
jd-analyzer --(Ineligible gate)--> STOP + log
  |
  v
resume-tailor  (master resume = single fact bank)
  |
  v
claim-verifier --(fail)--> fix, rerun
  |
  v
resume-pdf --> ats-check [fresh subagent] --(fail)--> fix (max 2 rounds)
  |
  v
resume-auditor [fresh subagent] --(fail)--> fix (max 2 rounds)
  |
  v
fill form (human-paced) --> form-auditor [fresh subagent, read-only] --(fail/unsure)--> fix (max 3)
  |
  v
application-tracker --> USER reviews and submits
```

## Why it is built this way
- **One verified master.** Every resume derives from it. A tailor can reorder and trim, never add. This removes the main failure mode of AI resume tools: invented claims.
- **Producer != checker.** An agent is biased toward its own output. Each gate runs in a new context with only the rubric and the inputs, so it cannot inherit the producer's reasoning.
- **Mix of mechanical and judged checks.** Scripts catch what is checkable (new numbers/tools/titles, PDF parse, format, keyword coverage). Rubric-based auditors judge density, relevance, a 10-second scan, interview-getting power. The ATS score is a heuristic, not a real ATS score; the fix for a failing check is to fix the cause, never to stuff keywords.
- **Bounded loops.** Max 2-3 fix rounds, then ask the human. Prevents endless self-grading.
- **Hard gates first.** Requirements (remote, location, pay floor, employer type) are checked before any tailoring effort. A failed gate is never promoted by a high fit score.
- **Human at every outward step.** The pipeline stops before submit. Free-text answers are drafted, shown, and approved before filling.
- **Evidence labels.** Verified / User estimate / Unverified / Missing keep estimates and gaps visible instead of buried.

## Scheduled discovery (separate from the per-job flow)
`job-scan` polls public ATS boards on a schedule, analyzes only new postings with `jd-analyzer`, and notifies only on strong fits. It never applies.

## What generalizes
Any agent workflow with a risky output (resume, release, PR, report) can use the same shape: spec the gates, give the producer a single fact source, check with a fresh context, cap the loops, keep a human on the irreversible step.
