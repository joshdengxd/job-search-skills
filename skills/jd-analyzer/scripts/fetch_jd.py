#!/usr/bin/env python3
"""Dump job-description text via official ATS APIs (no scraping).

usage: fetch_jd.py JOBS.json OUTDIR [url-substring ...]
       fetch_jd.py --url JOB_URL [OUTDIR]        (Greenhouse / Ashby / Lever posting URL; OUTDIR default ./jd)
JOBS.json = list of {src, company, url, id[, title, location]} (e.g. run_scan.py's inbox/new-DATE.json). Optional substrings select jobs by URL.
Writes OUTDIR/<company>-<n>.txt (title, location, url, comp, first ~9000 chars of description).
Greenhouse: also appends APPLICATION FORM NOTES (the form can restrict hiring to certain provinces even when the posting says 'Remote - Canada'). Ashby/Lever: open <job url>/application in the browser and read it.
"""
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ats_sources import get  # noqa: E402


def clean(h):
    h = h or ""
    if "&lt;" in h:  # Greenhouse returns entity-escaped HTML
        h = html.unescape(h)
    h = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", h, flags=re.I)
    h = html.unescape(re.sub(r"<[^>]+>", " ", h))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", h)).strip()


_ashby = {}


def text(j):
    s, c = j["src"], j["company"]
    if s == "greenhouse":
        d = get(f"https://boards-api.greenhouse.io/v1/boards/{c}/jobs/{j['id']}?pay_transparency=true&questions=true") or {}
        pay = "; ".join(f"{p.get('title')}: {p.get('min_cents', 0) // 100}-{p.get('max_cents', 0) // 100} {p.get('currency_type')}"
                        for p in d.get("pay_input_ranges") or [])
        form = []
        for q in d.get("questions") or []:
            desc = clean(q.get("description"))
            opts = [v.get("label") for f in q.get("fields", []) for v in f.get("values", [])]
            if desc or (opts and len(opts) > 4):
                form.append(f"- {q.get('label')}: {desc}" + (f" [options: {', '.join(opts[:20])}]" if len(opts) > 4 else ""))
        NL = chr(10)
        tail = (NL + NL + "=== APPLICATION FORM NOTES (check hiring-location/province/eligibility restrictions!) ===" + NL + NL.join(form)) if form else ""
        return clean(d.get("content")) + tail, pay
    if s == "ashby":
        if c not in _ashby:
            _ashby[c] = (get(f"https://api.ashbyhq.com/posting-api/job-board/{c}?includeCompensation=true") or {}).get("jobs", [])
        for x in _ashby[c]:
            if x.get("jobUrl") == j["url"]:
                comp = (x.get("compensation") or {}).get("scrapeableCompensationSalarySummary") or j.get("comp") or ""
                return x.get("descriptionPlain") or clean(x.get("descriptionHtml")), comp
    if s == "lever":
        for x in get(f"https://api.lever.co/v0/postings/{c}?mode=json") or []:
            if x["id"] == j["id"]:
                parts = [x.get("descriptionPlain") or ""] + [f"{l['text']}\n{clean(l['content'])}" for l in x.get("lists", [])]
                return "\n".join(parts + [x.get("additionalPlain") or ""]), j.get("comp") or ""
    return "(no JD text via API)", ""


def from_url(u):
    """Build a job dict from a Greenhouse / Ashby / Lever posting URL."""
    m = re.search(r"greenhouse\.io/(?:embed/job_app\?for=)?([\w-]+)/jobs/(\d+)", u) or re.search(r"[?&]gh_jid=(\d+)", u)
    if m and "greenhouse" in u:
        return dict(src="greenhouse", company=m.group(1), id=m.group(2), url=u.split("?")[0])
    if m:  # company career site with ?gh_jid= : board slug unknown
        sys.exit("gh_jid URL found but the Greenhouse board slug is unknown; pass the boards.greenhouse.io/<company>/jobs/<id> URL")
    m = re.search(r"ashbyhq\.com/([\w.-]+)/([0-9a-f-]{36})", u)
    if m:
        return dict(src="ashby", company=m.group(1), id=m.group(2), url=f"https://jobs.ashbyhq.com/{m.group(1)}/{m.group(2)}")
    m = re.search(r"lever\.co/([\w.-]+)/([0-9a-f-]{36})", u)
    if m:
        return dict(src="lever", company=m.group(1), id=m.group(2), url=u.split("?")[0])
    sys.exit("unsupported URL (need Greenhouse, Ashby or Lever); read the page with WebFetch instead")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        sys.exit(__doc__)
    if sys.argv[1] == "--url":
        if len(sys.argv) < 3:
            sys.exit(__doc__)
        jobs, out, sel = [from_url(sys.argv[2])], (sys.argv[3] if len(sys.argv) > 3 else "jd"), []
    else:
        if len(sys.argv) < 3:
            sys.exit(__doc__)
        jobs = json.load(open(sys.argv[1], encoding="utf-8"))
        out, sel = sys.argv[2], sys.argv[3:]
    os.makedirs(out, exist_ok=True)
    for i, j in enumerate(jobs):
        if sel and not any(x in j["url"] for x in sel):
            continue
        t, pay = text(j)
        safe = re.sub(r"[^\w.-]", "_", j["company"])
        fn = f"{out}/{safe}-{i}.txt"
        with open(fn, "w", encoding="utf-8") as f:
            f.write(f"{j.get('title', '')} | {j.get('location', '')} | {j['url']} | listed comp: {pay or j.get('comp') or 'none'}\n\n{t[:9000]}")
        print(fn, len(t))


if __name__ == "__main__":
    main()
