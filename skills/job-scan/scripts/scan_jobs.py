"""Board fetchers + filters (stdlib). Defaults target Senior (non-Staff/L6) SWE roles open to Canada: edit the filter
constants/functions below to retarget. run_scan.py imports this; standalone run writes ./jobs/scan-YYYY-MM-DD.json"""
import json, re, sys, datetime, urllib.request, concurrent.futures as cf

GH = []  # company slugs live in your data dir (boards.json), not here
ASHBY = []

TITLE = re.compile(r"(software|engineer|developer|front.?end|full.?stack|back.?end|web)", re.I)
SENIOR = re.compile(r"\bsenior\b|\bsr\.?\b", re.I)
EXCL = re.compile(r"workplace|data eng|analytics|consultant|quality|forward deployed|hardware|\bIT\b|enterprise systems|identity and access|staff|principal|manager|director|\blead\b|head of|machine learning|\bml\b|data scien|security|\bsre\b|site reliab|devops|\bios\b|android|mobile|embedded|firmware|sales|solutions|support|\bqa\b|\btest", re.I)
CAN = re.compile(r"canada|remote", re.I)

def get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "job-search-research"}), timeout=20) as r:
            return json.load(r)
    except Exception:
        return None

def gh(slug):
    d = get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
    out = []
    for j in (d or {}).get("jobs", []):
        t, loc = j["title"], j["location"]["name"]
        if TITLE.search(t) and SENIOR.search(t) and not EXCL.search(t) and re.search(r"canada", loc, re.I):
            if not (re.search("remote", loc, re.I) or re.fullmatch("(CA - )?Canada", loc.strip(), re.I)):
                continue
            out.append(dict(src="greenhouse", company=slug, title=t, location=loc, url=j["absolute_url"], updated=j.get("updated_at"), id=j["id"]))
    return out

def ashby(slug):
    d = get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true")
    out = []
    for j in (d or {}).get("jobs", []):
        t = j["title"]; loc = (j.get("location") or "") + " " + " ".join((s.get("location") or "") for s in (j.get("secondaryLocations") or []))
        if TITLE.search(t) and (j.get("isRemote") or "remote" in loc.lower()) and SENIOR.search(t) and not EXCL.search(t) and re.search(r"canada", loc + (((j.get("address") or {}).get("postalAddress") or {}).get("addressCountry") or ""), re.I):
            comp = (j.get("compensation") or {}).get("compensationTierSummary")
            out.append(dict(src="ashby", company=slug, title=t, location=loc.strip(), url=j["jobUrl"], updated=j.get("publishedAt"), remote=j.get("isRemote"), comp=comp))
    return out

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    jobs = []
    # usage: scan_jobs.py [--gh a,b] [--ashby c,d]  (custom slugs replace the default lists)
    a = dict(zip(sys.argv[1::2], sys.argv[2::2]))
    g = a["--gh"].split(",") if "--gh" in a else GH
    h = a["--ashby"].split(",") if "--ashby" in a else ASHBY
    with cf.ThreadPoolExecutor(16) as ex:
        for r in list(ex.map(gh, dict.fromkeys(g))) + list(ex.map(ashby, dict.fromkeys(h))):
            jobs += r
    f = f"jobs/scan-{datetime.date.today()}" + ("-extra" if a else "") + ".json"
    json.dump(jobs, open(f, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for j in sorted(jobs, key=lambda x: x["company"]):
        print(j["company"], "|", j["title"], "|", j["location"], "|", j["url"], "|", j.get("comp") or "")
    print(len(jobs), "->", f)
