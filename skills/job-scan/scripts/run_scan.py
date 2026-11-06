#!/usr/bin/env python3
"""Job pipeline helper (stdlib only). Run from the project dir that holds your data.

  Global option: --data-dir DIR (default ./jobs) = where seen.json, state.json, inbox/, opportunities.csv live.
  Env: SCAN_EXCLUDE=slug1,slug2 or <data-dir>/exclude.txt add board slugs to skip; boards come from <data-dir>/boards.json (or --boards FILE); none are shipped.

  run_scan.py scan [--dry]        scan Greenhouse/Ashby; write only UNSEEN jobs to jobs/inbox/new-DATE.json
  run_scan.py baseline            seed jobs/seen.json with everything currently visible (no report)
  run_scan.py li-add FILE [--dry] FILE = JSON list [{id,title,company,location,url}] from LinkedIn alert emails;
                                  prints only UNSEEN ones (also unseen by company+title) and records them
  run_scan.py append-csv FILE     append analyzed rows (JSON list of dicts) to jobs/opportunities.csv
  run_scan.py state [--set-run]   print / bump jobs/state.json last_run
"""
import csv
import datetime
import glob
import json
import os
import re
import sys
import concurrent.futures as cf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scan_jobs as sj  # noqa: E402
import ats_sources as A  # noqa: E402
import extra_sources as X  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
JOBS = "jobs"
BOARDS = ""
SEEN = STATE = OPP = ""


def configure(data_dir, boards=None):
    global JOBS, SEEN, STATE, OPP, BOARDS
    JOBS = data_dir.rstrip("/\\")
    SEEN, STATE, OPP = f"{JOBS}/seen.json", f"{JOBS}/state.json", f"{JOBS}/opportunities.csv"
    BOARDS = boards or f"{JOBS}/boards.json"


configure(JOBS)
NEW_COLS = ["first_seen", "fit_tier", "source", "analysis"]
TODAY = str(datetime.date.today())


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def ct(company, title):
    return f"{norm(company)}|{norm(title)}"


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)


def strip_q(url):
    return (url or "").split("?")[0].split("#")[0].rstrip("/")


class Seen:
    def __init__(self):
        self.d = load(SEEN, {"jobs": {}})
        self.cts = {v["ct"] for v in self.d["jobs"].values() if v.get("ct")}

    def known(self, key, c):
        return key in self.d["jobs"] or c in self.cts

    def add(self, key, company, title, url, src):
        c = ct(company, title)
        self.d["jobs"][key] = dict(first_seen=TODAY, company=company, title=title, url=url, src=src, ct=c)
        self.cts.add(c)

    def save(self):
        save(SEEN, self.d)


def ats_key(j):
    return f"{j['src']}:{strip_q(j['url'])}"


# Nothing excluded by default. Add slugs via env SCAN_EXCLUDE=slug,slug or <data-dir>/exclude.txt.
EXCLUDE = {x for x in os.environ.get("SCAN_EXCLUDE", "").split(",") if x}


def excluded():
    """Defaults + env SCAN_EXCLUDE + optional <data-dir>/exclude.txt (whitespace/comma separated slugs)."""
    f = f"{JOBS}/exclude.txt"
    extra = set(re.split(r"[\s,]+", open(f, encoding="utf-8").read().strip())) - {""} if os.path.exists(f) else set()
    return EXCLUDE | extra


def boards():
    """All (ats, slug) to scan: boards.json (from discover_boards.py) + the original hand-picked GH/Ashby slugs."""
    b = {k: list(v) for k, v in load(BOARDS, {}).get("boards", {}).items()}
    b.setdefault("greenhouse", [])
    b.setdefault("ashby", [])
    b["greenhouse"] = list(dict.fromkeys(b["greenhouse"] + sj.GH))
    b["ashby"] = list(dict.fromkeys(b["ashby"] + sj.ASHBY))
    return [(ats, slug) for ats, slugs in b.items() for slug in slugs if slug not in excluded()]


def one(t):
    ats, slug = t
    try:
        r = A.fetch(ats, slug)
        return r[1] if r else []
    except Exception as e:  # one bad board must not kill the run
        print(f"warn: {ats}:{slug} {e!r}", file=sys.stderr)
        return []


def run_scan():
    jobs = []
    with cf.ThreadPoolExecutor(24) as ex:
        for r in ex.map(one, boards()):
            jobs += r
    jobs += X.fetch_all(load(f"{JOBS}/extra-sources.json", {}))  # company-feed sources (not on ATS boards)
    return jobs


def cmd_scan(args):
    seen = Seen()
    jobs = run_scan()
    new = [j for j in jobs if not seen.known(ats_key(j), ct(j["company"], j["title"]))]
    for j in new:
        seen.add(ats_key(j), j["company"], j["title"], j["url"], j["src"])
        j["key"] = ats_key(j)
    if "--dry" not in args:
        seen.save()
        save(f"{JOBS}/inbox/new-{TODAY}.json", new)
    for j in sorted(new, key=lambda x: x["company"]):
        print(j["company"], "|", j["title"], "|", j["location"], "|", j["url"], "|", j.get("comp") or "")
    print(f"scanned={len(jobs)} new={len(new)}")


def cmd_baseline(_):
    seen = Seen()
    n0 = len(seen.d["jobs"])
    for j in run_scan():
        seen.add(ats_key(j), j["company"], j["title"], j["url"], j["src"])
    for f in glob.glob(f"{JOBS}/scan-*.json"):
        for j in load(f, []):
            seen.add(ats_key(j), j["company"], j["title"], j["url"], j["src"])
    for f in (OPP, f"{JOBS}/applications.csv"):
        if os.path.exists(f):
            with open(f, encoding="utf-8-sig", newline="") as fh:
                for r in csv.DictReader(fh):
                    if r.get("url"):
                        seen.add(f"csv:{strip_q(r['url'])}", r.get("company", ""), r.get("title") or r.get("role", ""), r["url"], "csv")
    seen.save()
    print(f"seen: {n0} -> {len(seen.d['jobs'])}")


def cmd_li_add(args):
    items = load(args[0], [])
    seen = Seen()
    out = []
    for it in items:
        jid = re.search(r"(\d{6,})", str(it.get("id") or it.get("url", "")))
        key = f"li:{jid.group(1)}" if jid else f"li:{strip_q(it.get('url'))}"
        if seen.known(key, ct(it.get("company"), it.get("title"))):
            continue
        seen.add(key, it.get("company", ""), it.get("title", ""), it.get("url", ""), "linkedin-alert")
        out.append(dict(it, key=key))
    if "--dry" not in args:
        seen.save()
    print(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"li_in={len(items)} li_new={len(out)}", file=sys.stderr)


def cmd_append_csv(args):
    rows = load(args[0], [])
    with open(OPP, encoding="utf-8-sig", newline="") as f:
        rd = list(csv.reader(f))
    header = rd[0]
    for c in NEW_COLS:
        if c not in header:
            header.append(c)
    body = [r + [""] * (len(header) - len(r)) for r in rd[1:]]
    for r in rows:
        r.setdefault("first_seen", TODAY)
        r.setdefault("date_checked", TODAY)
        body.append([str(r.get(c, "")) for c in header])
    with open(OPP, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(body)
    print(f"appended {len(rows)} -> {len(body)} rows")


def cmd_state(args):
    s = load(STATE, {})
    if "--set-run" in args:
        s["last_run"] = TODAY
        save(STATE, s)
    print(json.dumps(s))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    cmds = dict(scan=cmd_scan, baseline=cmd_baseline, **{"li-add": cmd_li_add, "append-csv": cmd_append_csv}, state=cmd_state)
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    argv = sys.argv[2:]
    dd, bf = JOBS, None
    for flag in ("--data-dir", "--boards"):
        if flag in argv:
            i = argv.index(flag)
            val = argv[i + 1]
            del argv[i:i + 2]
            if flag == "--data-dir":
                dd = val
            else:
                bf = val
    configure(dd, bf)
    cmds[sys.argv[1]](argv)
