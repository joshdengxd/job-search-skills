#!/usr/bin/env python3
"""Flag numbers and tool-like tokens in TAILORED that are absent from MASTER. Stdlib only."""
import re
import sys

NUM = re.compile(r"\$?\d[\d,.]*\s?(?:k|K|m|M|%|\+|x)?")
TOK = re.compile(r"[A-Za-z][A-Za-z0-9.+#/_-]*")
COMMON = set(
    """the and for with that this from into over under using built led new use used end per via your our their
    senior software engineer developer full stack summary experience skills education selected project present
    jan feb mar apr may jun jul aug sep oct nov dec""".split()
)


def tokens(text):
    text = re.sub(r"\[CONFIRM[^\]]*\]", " ", text)
    nums = {re.sub(r"\s", "", n).lower().rstrip(".,") for n in NUM.findall(text)}
    toks = set()
    for t in TOK.findall(text):
        low = t.lower().strip(".-")
        if len(low) < 3 or low in COMMON:
            continue
        if t[0].isupper() or any(c.isupper() for c in t[1:]) or any(c in t for c in "0123456789.+#/"):
            toks.add(low)
    return nums, toks


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: verify.py MASTER TAILORED")
    master = open(sys.argv[1], encoding="utf-8").read()
    tailored = open(sys.argv[2], encoding="utf-8").read()
    mn, mt = tokens(master)
    tn, tt = tokens(tailored)
    bad_n, bad_t = sorted(tn - mn), sorted(tt - mt)
    print("NUMBERS not in master:", bad_n or "none")
    print("TOKENS not in master:", bad_t or "none")
    sys.exit(1 if bad_n or bad_t else 0)


if __name__ == "__main__":
    main()
