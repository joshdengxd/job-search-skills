"""Readers for companies that are NOT on the standard public ATS boards but publish an official JSON careers feed.

Configure per company in `<data-dir>/extra-sources.json`: {"<company>": "<careers-listings JSON URL>"}. Add new readers to READERS below.
Each reader returns job dicts like ats_sources.fetch(): src, company, title, location, url, updated, comp, id.
Official public endpoints only; no login, no job-board scraping. Companies without a feed go in the manual watchlist (see SKILL.md step 2b).
"""
import html
import json
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (job-search-research)", "Accept": "application/json"}
SKIP = re.compile(r"intern|graduate|new grad|principal|staff|manager|director|\blead\b|head of|machine learning|\bml\b|"
                  r"security|\bsre\b|reliab|devops|\bios\b|android|mobile|embedded|firmware|sales|solutions|support|\bqa\b|\btest|data scien|analytics", re.I)
ROLE = re.compile(r"software|engineer|developer|front.?end|full.?stack|back.?end", re.I)


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def listings_json(company, url):
    """Careers listings feed (list of jobs with title/locations/category/portalJobPost). Keep Canada + remote engineering roles.
    Remote-location rules (timezone/province) are in the description text; surfaced in `note`."""
    data = _get(url)
    out = []
    for j in data:
        locs = " | ".join(j.get("locations") or [])
        if not (re.search(r"canada", locs, re.I) and re.search(r"remote", locs, re.I)):
            continue
        t = j["title"]
        if not ROLE.search(t) or SKIP.search(t) or (j.get("category") or "") != "Engineering":
            continue
        text = html.unescape(re.sub(r"<[^>]+>", " ", " ".join(j.get(k, "") or "" for k in ("overview", "responsibilities", "qualifications"))))
        text = re.sub(r"\s+", " ", text)
        m = re.search(r"[^.]*(located in|from any location in|timezone|time zone)[^.]*\.", text, re.I)
        pay = re.search(r"Canada:\s*(CA\$[\d,]+\s*-\s*CA\$[\d,]+)", text)
        out.append(dict(src=company, company=company, title=t, location=locs,
                        url=j["portalJobPost"]["portalUrl"], updated=j["portalJobPost"].get("updatedDate"),
                        comp=pay.group(1) if pay else None, id=str(j["id"]),
                        note=m.group(0).strip()[:200] if m else ""))
    return out


READERS = {"listings_json": listings_json}


def fetch_all(enabled):
    jobs = []
    for name, url in (enabled or {}).items():
        if isinstance(url, str) and url:
            try:
                jobs += READERS["listings_json"](name, url)
            except Exception as e:  # one broken feed must not kill the run
                print(f"warn: extra source {name}: {e!r}")
    return jobs
