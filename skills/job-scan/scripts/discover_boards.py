#!/usr/bin/env python3
"""Find which public ATS boards exist for a list of companies -> <data-dir>/boards.json (the board list run_scan.py uses).

usage: discover_boards.py [--data-dir DIR] [--names FILE] [--min-jobs N] [--extra name1,name2]
  --names FILE: whitespace-separated company names (default <data-dir>/discover-names.txt); none are shipped.
Probes Greenhouse/Ashby/Lever/SmartRecruiters/Workable/Recruitee with slug variants of each name.
Keeps boards with >= N open postings (size proxy for "100+ employees"; default 10). Merges into existing boards.json.
Real company size is verified later (jd-analyzer).
"""
import concurrent.futures as cf
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ats_sources as A  # noqa: E402



def variants(n):
    j = n.replace("-", "")
    out = [n, j, j + "hq"]
    return list(dict.fromkeys(out))


def probe(args):
    ats, slug = args
    r = A.fetch(ats, slug)
    return (ats, slug, r[0]) if r else None


def main():
    a = dict(zip(sys.argv[1::2], sys.argv[2::2]))
    min_jobs = int(a.get("--min-jobs", 10))
    dd = a.get("--data-dir", "jobs")
    OUT = os.path.join(dd, "boards.json")
    nf = a.get("--names", os.path.join(dd, "discover-names.txt"))
    base_names = open(nf, encoding="utf-8").read().split() if os.path.exists(nf) else []
    names = list(dict.fromkeys(base_names + (a.get("--extra", "").split(",") if a.get("--extra") else [])))
    tasks = [(ats, v) for n in names for v in variants(n) for ats in A.FETCHERS]
    print(f"probing {len(names)} names, {len(tasks)} requests...", file=sys.stderr)
    found = {}
    with cf.ThreadPoolExecutor(24) as ex:
        for r in ex.map(probe, tasks):
            if r and r[2] >= min_jobs:
                found.setdefault(r[0], {})[r[1]] = r[2]
    cur = {}
    if os.path.exists(OUT):
        cur = json.load(open(OUT, encoding="utf-8")).get("boards", {})
    for ats, d in found.items():
        cur.setdefault(ats, {}).update(d)
    json.dump({"generated": str(datetime.date.today()), "min_jobs": min_jobs, "boards": cur},
              open(OUT, "w", encoding="utf-8"), indent=1, sort_keys=True)
    for ats, d in sorted(cur.items()):
        print(ats, len(d))


if __name__ == "__main__":
    main()
