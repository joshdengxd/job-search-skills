#!/usr/bin/env python3
"""Portability lint: each skills/<name>/ must be shareable alone.
Flags project-root paths, absolute local paths, emails, phone numbers.
Optional: --denylist FILE (one regex per line, '#' comments) for private strings kept outside this repo.
usage: python tools/lint_skills.py [skills_dir] [--denylist FILE]   exit 1 if any finding
"""
import os
import re
import sys

args = [a for a in sys.argv[1:]]
deny_file = None
if "--denylist" in args:
    i = args.index("--denylist")
    deny_file = args[i + 1]
    del args[i : i + 2]
root = args[0] if args else "skills"

BAD = [
    (r"(?<![\w./-])(profile|research|archive|companies|linkedin|docs)/[\w.-]", "project dir path"),
    (r"(?<![\w./-])scripts/(?!terms|requirements)", "root scripts/ path"),
    (r"AGENTS\.md|CLAUDE\.md", "project rules file"),
    (r"[A-Za-z]:[\\/](?:Users|\w*workspace)|/Users/\w+|/home/\w+", "absolute local path"),
    (r"[\w.+-]+@(?!linkedin\.com)[\w-]+\.[\w.-]+", "email address"),
    (r"\b\d{3}[-. )]\s?\d{3}[-. ]\d{4}\b", "phone number"),
    (r"resumes/", "project resumes/ path"),
]
if deny_file:
    with open(deny_file, encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                BAD.append((ln, "denylist"))

n = 0
for d in sorted(os.listdir(root)):
    base = os.path.join(root, d)
    if not os.path.isdir(base):
        continue
    for dp, dn, fn in os.walk(base):
        dn[:] = [x for x in dn if x not in ("__pycache__",)]
        for f in fn:
            if not f.endswith((".md", ".py", ".json", ".txt", ".csv")) or f == "boards.json":
                continue
            p = os.path.join(dp, f)
            for i, line in enumerate(open(p, encoding="utf-8-sig", errors="replace"), 1):
                for pat, why in BAD:
                    if re.search(pat, line, re.I):
                        n += 1
                        print(f"{p}:{i}: [{why}] {line.strip()[:110]}")
    if not os.path.exists(os.path.join(base, "SKILL.md")):
        n += 1
        print(f"{base}: missing SKILL.md")
print(f"{n} finding(s)")
sys.exit(1 if n else 0)
