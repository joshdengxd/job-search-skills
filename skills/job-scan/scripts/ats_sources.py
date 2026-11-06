"""Public ATS job-board readers (stdlib only). Official public APIs, no login, no scraping of job boards.

fetch(ats, slug) -> None (board missing) | (total_open_jobs, [matching jobs])
Matching = Senior title, not excluded role, Canada-eligible location (+ remote flag when the ATS exposes one).
Job dict: src, company(slug), title, location, url, updated, comp, id
"""
import json
import re
import urllib.request

UA = {"User-Agent": "job-search-research"}

TITLE = re.compile(r"(software|engineer|developer|front.?end|full.?stack|back.?end|web)", re.I)
SENIOR = re.compile(r"\bsenior\b|\bsr\.?\b", re.I)
EXCL = re.compile(
    r"workplace|data eng|analytics|consultant|quality|forward deployed|hardware|\bIT\b|enterprise systems|identity and access|staff|principal|manager|director|\blead\b|head of|"
    r"machine learning|\bml\b|data scien|security|\bsre\b|site reliab|devops|\bios\b|android|mobile|embedded|firmware|"
    r"sales|solutions|support|\bqa\b|\btest",
    re.I,
)
CAN = re.compile(r"canada|\bCA\b", re.I)


def get(url, data=None):
    try:
        req = urllib.request.Request(url, data=data, headers=UA)
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    except Exception:
        return None


def ok_title(t):
    return bool(TITLE.search(t) and SENIOR.search(t) and not EXCL.search(t))


def lever(slug):
    d = get(f"https://api.lever.co/v0/postings/{slug}?mode=json")
    if not isinstance(d, list) or not d:
        return None
    out = []
    for j in d:
        c = j.get("categories") or {}
        locs = " ".join([c.get("location") or ""] + list(c.get("allLocations") or []))
        canada = bool(CAN.search(locs)) or (j.get("country") or "").upper() == "CA"
        remote = (j.get("workplaceType") == "remote") or "remote" in locs.lower()
        if ok_title(j["text"]) and canada and remote:
            sr = j.get("salaryRange") or {}
            comp = f"{sr.get('min')}-{sr.get('max')} {sr.get('currency')}/{sr.get('interval')}" if sr else None
            out.append(dict(src="lever", company=slug, title=j["text"], location=locs.strip(), url=j["hostedUrl"],
                            updated=j.get("createdAt"), comp=comp, id=j["id"]))
    return len(d), out


def smartrecruiters(slug):
    t = get(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=1")
    if not t or not t.get("totalFound"):
        return None
    d = get(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100&country=ca") or {}
    out = []
    for j in d.get("content", []):
        loc = j.get("location") or {}
        if ok_title(j["name"]) and loc.get("remote"):
            out.append(dict(src="smartrecruiters", company=slug, title=j["name"],
                            location=", ".join(filter(None, [loc.get("city"), loc.get("region"), loc.get("country")])),
                            url=f"https://jobs.smartrecruiters.com/{slug}/{j['id']}", updated=j.get("releasedDate"),
                            comp=None, id=j["id"]))
    return t["totalFound"], out


def workable(slug):
    d = get(f"https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true")
    if not d or not d.get("jobs"):
        return None
    out = []
    for j in d["jobs"]:
        loc = ", ".join(filter(None, [j.get("city"), j.get("state"), j.get("country")]))
        if ok_title(j["title"]) and j.get("telecommuting") and CAN.search(loc):
            out.append(dict(src="workable", company=slug, title=j["title"], location=loc,
                            url=j.get("url") or j.get("application_url"), updated=j.get("published_on"),
                            comp=None, id=j.get("shortcode")))
    return len(d["jobs"]), out


def recruitee(slug):
    d = get(f"https://{slug}.recruitee.com/api/offers/")
    if not d or not d.get("offers"):
        return None
    out = []
    for o in d["offers"]:
        loc = o.get("location") or ""
        canada = (o.get("country_code") or "").upper() == "CA" or bool(CAN.search(loc))
        if ok_title(o["title"]) and o.get("remote") and canada:
            out.append(dict(src="recruitee", company=slug, title=o["title"], location=loc, url=o.get("careers_url"),
                            updated=o.get("created_at"), comp=None, id=o.get("id")))
    return len(d["offers"]), out


def _gh(slug):
    from scan_jobs import gh, get as g
    d = g(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
    if not d or not d.get("jobs"):
        return None
    return len(d["jobs"]), gh(slug)


def _ashby(slug):
    from scan_jobs import ashby, get as g
    d = g(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    if not d or not d.get("jobs"):
        return None
    return len(d["jobs"]), ashby(slug)


FETCHERS = dict(greenhouse=_gh, ashby=_ashby, lever=lever, smartrecruiters=smartrecruiters, workable=workable,
                recruitee=recruitee)


def fetch(ats, slug):
    try:
        return FETCHERS[ats](slug)
    except Exception:
        return None
