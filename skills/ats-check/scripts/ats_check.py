#!/usr/bin/env python3
"""Local ATS-readiness check for a resume PDF. No network, no LLM, deterministic.

usage: ats_check.py RESUME.pdf [--jd JD.txt] [--master master-resume.md]
                    [--terms terms.json] [--save] [--out REPORT.json] [--json]

What it does (density/length/format rules follow common resume guidance):
  1. PARSE   - extracts text with 3 independent parsers (PyMuPDF, pdfplumber, pdfium);
               checks ligatures/garbage, headings, parser agreement, reading order.
  2. FORMAT  - images, tables, columns, contact in header/footer, length/fill, bullet
               density, dates, font size, placeholders.
  3. KEYWORDS- (needs --jd) JD tech/skill terms vs resume. Terms absent from the resume
               but present in master-resume.md = "add if true & relevant". Terms absent
               from both = Missing (never add). Score uses ONLY the achievable set.

The 0-100 score is a heuristic summary of those checks, NOT a real ATS score. Optimize
the failing checks, not the number. Never add a keyword you cannot defend in an interview.
Exit code: 0 PASS (score>=90, no hard fail), 1 FIX (score<90), 2 FAIL (hard fail).
"""
import argparse
import datetime
import difflib
import json
import os
import re
import statistics
import sys

import fitz  # PyMuPDF
fitz.TOOLS.mupdf_display_errors(False)
import pdfplumber
import pypdfium2 as pdfium

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------- vocabulary
# canonical -> aliases (all matched case-insensitively with token boundaries)
def load_terms(path=None):
    """Vocabulary: canonical term -> aliases. Edit terms.json (next to this script) to add your own."""
    p = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "terms.json")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


TERMS = load_terms()
NICE_MARK = re.compile(r"(nice[- ]to[- ]have|bonus|preferred|a plus|good to have|great to have|"
                       r"would be a plus|is a plus|are a plus|extra credit|ideal)", re.I)
SECTIONS = {"summary": r"(professional )?summary|profile|about( me)?",
            "experience": r"(work |professional )?experience|employment( history)?",
            "skills": r"(technical |core )?skills|technologies",
            "education": r"education"}
MON = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?"
DATE_RANGE = re.compile(rf"({MON}\s+\d{{4}}|\d{{4}})\s*[–—-]\s*(Present|Current|{MON}\s+\d{{4}}|\d{{4}})", re.I)
BULLETS = "•▪◦●‣∙·-–*"
PASS_SCORE = 90  # workflow gate: PASS needs score >= 90 and no hard fail
LIGATURES = re.compile("[ﬀ-ﬆ]")
BADCHARS = re.compile("[�-]")


def norm(s):
    return re.sub(r"\s+", " ", s.lower())


def term_re(alias):
    return re.compile(r"(?<![\w#+./-])" + re.escape(alias.lower()) + r"(?![\w#+]|\.\w)", re.I)


TERM_RES = {c: [term_re(a) for a in al] for c, al in TERMS.items()}


def has_term(text, canon):
    t = norm(text)
    return any(r.search(t) for r in TERM_RES[canon])


def count_term(text, canon):
    t = norm(text)
    return sum(len(r.findall(t)) for r in TERM_RES[canon])


# ---------------------------------------------------------------- extraction
def extract_all(path):
    out = {}
    d = fitz.open(path)
    out["pymupdf"] = "\n".join(p.get_text("text") for p in d)
    with pdfplumber.open(path) as pl:
        out["pdfplumber"] = "\n".join((p.extract_text() or "") for p in pl.pages)
    pd = pdfium.PdfDocument(path)
    out["pdfium"] = "\n".join(pd[i].get_textpage().get_text_range() for i in range(len(pd)))
    for k in out:
        out[k] = out[k].replace("\r", "")
    return out


def tokens(s):
    return re.findall(r"[a-z0-9#+.]+", s.lower())


# ---------------------------------------------------------------- check plumbing
CHECKS = []


def add(cid, group, status, pts, mx, msg):
    earned = {"PASS": mx, "WARN": mx * 0.5, "FAIL": 0}[status] if pts is None else pts
    CHECKS.append(dict(id=cid, group=group, status=status, pts=round(earned, 1), max=mx, msg=msg))


def headings(text):
    found = {}
    for i, line in enumerate(text.splitlines()):
        s = line.strip().strip(":").strip()
        for k, pat in SECTIONS.items():
            if k not in found and re.fullmatch(pat, s, re.I):
                found[k] = i
    return found


# ---------------------------------------------------------------- PDF structure
def layout_info(path):
    d = fitz.open(path)
    info = dict(pages=len(d), images=0, tables=0, col_pairs=0, min_font=99.0, fonts=set(),
                last_fill=0.0, contact_zone=[], lines=[])
    sizes = []
    for pi, page in enumerate(d):
        h, w = page.rect.height, page.rect.width
        info["images"] += len(page.get_images(full=True))
        try:
            info["tables"] += sum(1 for t in page.find_tables().tables if t.row_count >= 2 and t.col_count >= 2)
        except Exception:
            pass
        lines = []
        for b in page.get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                txt = "".join(s["text"] for s in ln["spans"]).strip()
                if not txt:
                    continue
                for s in ln["spans"]:
                    if s["text"].strip():
                        sizes.append(s["size"])
                        info["fonts"].add(s["font"])
                lines.append((fitz.Rect(ln["bbox"]), txt, ln["spans"][0]["size"], pi))
        info["lines"].extend(lines)
        # two-column test: long lines side by side at the same height
        long_ = [(r, t) for r, t, _, _ in lines if len(t) > 25]
        for i in range(len(long_)):
            for j in range(i + 1, len(long_)):
                a, b2 = long_[i][0], long_[j][0]
                ov = min(a.y1, b2.y1) - max(a.y0, b2.y0)
                if ov > 0.5 * min(a.height, b2.height) and (b2.x0 - a.x1 > 15 or a.x0 - b2.x1 > 15):
                    info["col_pairs"] += 1
        for r, t, _, _ in lines:
            if re.search(r"@|\d{3}[-.\s]\d{3}[-.\s]\d{4}", t) and (r.y0 < 30 or r.y1 > h - 30):
                info["contact_zone"].append(t[:50])
        if pi == len(d) - 1 and lines:
            info["last_fill"] = max(r.y1 for r, _, _, _ in lines) / h
    if sizes:
        info["min_font"] = min(sizes)
        info["body_font"] = statistics.median(sizes)
    return info


def bullet_stats(lines):
    """Group PDF lines into roles (by date-range line) and bullets (by leading glyph)."""
    roles, cur_role, cur_b = [], None, None
    for r, t, size, _ in lines:
        if any(re.fullmatch(pt, t.strip(), re.I) for pt in SECTIONS.values()):
            cur_role, cur_b = None, None
            continue
        m = DATE_RANGE.search(t)
        is_b = t[0] in BULLETS and len(t) > 1 and (t[1] == " " or t[0] in "•▪◦●‣∙")
        if m and not is_b and len(t) < 140:
            cur_role = dict(header=t[:60], end=m.group(2), bullets=[])
            roles.append(cur_role)
            cur_b = None
        elif is_b and cur_role is not None:
            cur_b = dict(words=len(t.split()) - 1, lines=1)
            cur_role["bullets"].append(cur_b)
        elif cur_b is not None and cur_role is not None and r.x0 > 20 and size < 12 and not re.fullmatch(r"[A-Z &/]{3,}", t):
            cur_b["words"] += len(t.split())
            cur_b["lines"] += 1
        else:
            cur_b = None
    return roles


# ---------------------------------------------------------------- checks
def run_parse_checks(texts, path):
    base = texts["pymupdf"]
    ok = all(len(t.strip()) > 300 for t in texts.values())
    add("P1 extractable", "parse", "PASS" if ok else "FAIL", None, 5,
        "text extracted by all 3 parsers" if ok else "a parser got <300 chars (image-only/odd encoding?)")
    lig = {k: len(LIGATURES.findall(v)) for k, v in texts.items()}
    bad = {k: len(BADCHARS.findall(v)) for k, v in texts.items()}
    if sum(bad.values()):
        add("P2 clean text", "parse", "FAIL", None, 8, f"garbage/private-use chars: {bad}")
    elif sum(lig.values()):
        ex = {k: v for k, v in lig.items() if v}
        add("P2 clean text", "parse", "WARN", None, 8,
            f"ligature glyphs (fi/fl etc.) in text layer {ex}: keyword match can break, re-render PDF")
    else:
        add("P2 clean text", "parse", "PASS", None, 8, "no ligatures/garbage")
    hs = {k: headings(v) for k, v in texts.items()}
    need = ["experience", "skills", "education"]
    miss = {k: [n for n in need if n not in h] for k, h in hs.items()}
    allmiss = sorted({n for m in miss.values() for n in m})
    nosum = [k for k, h in hs.items() if "summary" not in h]
    if allmiss:
        add("P3 headings", "parse", "FAIL", None, 7, f"standard headings not found: {allmiss} ({miss})")
    elif nosum:
        add("P3 headings", "parse", "WARN", None, 7, "no Summary/Profile heading")
    else:
        add("P3 headings", "parse", "PASS", None, 7, "Summary/Experience/Skills/Education found in all parsers")
    tk = {k: tokens(v) for k, v in texts.items()}
    pairs = [("pymupdf", "pdfplumber"), ("pymupdf", "pdfium"), ("pdfplumber", "pdfium")]
    rat = {}
    for a, b in pairs:
        rat[f"{a}/{b}"] = round(difflib.SequenceMatcher(None, tk[a], tk[b], autojunk=False).ratio(), 3)
    lo = min(rat.values())
    st = "PASS" if lo >= 0.95 else "WARN" if lo >= 0.85 else "FAIL"
    add("P4 parser agreement", "parse", st, None, 8,
        f"token-order similarity {rat} (low = reading order differs across parsers)")


def run_format_checks(info):
    c = info["col_pairs"]
    if info["images"] or info["tables"]:
        add("F1 no images/tables", "format", "FAIL", None, 5,
            f"{info['images']} image(s), {info['tables']} table(s) (A5)")
    elif c >= 6:
        add("F1 no images/tables", "format", "FAIL", None, 5, f"looks multi-column ({c} side-by-side long lines) (A5)")
    else:
        add("F1 no images/tables", "format", "PASS", None, 5, "no images, tables, or columns detected")
    if info["contact_zone"]:
        add("F2 contact in body", "format", "WARN", None, 5, f"contact in header/footer zone: {info['contact_zone']}")
    else:
        add("F2 contact in body", "format", "PASS", None, 5, "contact not in header/footer zone")
    p, fill = info["pages"], info["last_fill"]
    if p == 1:
        st = "PASS" if fill >= 0.80 else "WARN"
        msg = f"1 page, filled to {fill:.0%}" + ("" if st == "PASS" else " (short, room to add proof)")
    elif p == 2:
        st = "PASS" if fill >= 0.50 else "FAIL"
        msg = f"2 pages, page 2 filled to {fill:.0%}" + ("" if st == "PASS" else " (<50%: trim to 1 page or fill)")
    else:
        st, msg = "FAIL", f"{p} pages"
    add("F3 length", "format", st, None, 5, msg)
    roles = bullet_stats(info["lines"])
    probs, warns = [], []
    yr = datetime.date.today().year
    for i, r in enumerate(roles):
        n = len(r["bullets"])
        old = False
        m = re.search(r"(\d{4})", r["end"])
        if m and not re.search("present|current", r["end"], re.I):
            old = yr - int(m.group(1)) >= 3
        if i == 0 and n > 5:
            probs.append(f"latest role has {n} bullets (>5)")
        if i > 0 and old and n > 3:
            probs.append(f"'{r['header'][:30]}' has {n} bullets (>3, older role)")
        long_ = [b for b in r["bullets"] if b["words"] > 45 or b["lines"] > 3]
        mid = [b for b in r["bullets"] if (b["words"] > 32 or b["lines"] > 2)]
        if long_:
            probs.append(f"{len(long_)} bullet(s) >45 words/3 lines in '{r['header'][:30]}'")
        if len(mid) > 1:
            warns.append(f"{len(mid)} bullets >2 lines/32 words in '{r['header'][:30]}' (max 1 flagship)")
    if not roles or not any(r["bullets"] for r in roles):
        add("F4 density", "format", "WARN", None, 5, "could not detect roles/bullets in PDF text")
    else:
        st = "FAIL" if probs else "WARN" if warns else "PASS"
        add("F4 density", "format", st, None, 5,
            "; ".join(probs + warns) if (probs or warns) else
            f"{len(roles)} roles, bullets/role {[len(r['bullets']) for r in roles]}")
    mf = info.get("min_font", 99)
    st = "PASS" if mf >= 8.5 else "WARN" if mf >= 8 else "FAIL"
    add("F5 font size", "format", st, None, 3, f"min font {mf:.1f}pt, body ~{info.get('body_font', 0):.1f}pt")


def run_text_checks(text):
    ph = re.findall(r"\[(?:CONFIRM|TODO|TBD)[^\]]*\]|\[ \]|lorem ipsum", text, re.I)
    add("F6 no placeholders", "format", "FAIL" if ph else "PASS", None, 4,
        f"placeholders: {ph[:3]}" if ph else "none (A3)")
    n = len(DATE_RANGE.findall(text))
    add("F7 dates", "format", "PASS" if n >= 2 else "WARN", None, 3,
        f"{n} standard date ranges (Mon YYYY – Mon YYYY)")
    em = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    ph_ = re.search(r"\d{3}[-.\s]?\d{3}[-.\s]?\d{4}", text)
    add("F8 contact present", "format", "PASS" if em and ph_ else "WARN" if em else "FAIL", None, 3,
        f"email={'yes' if em else 'NO'} phone={'yes' if ph_ else 'NO'}")


def jd_terms(jd):
    m = NICE_MARK.search(jd)
    req, nice = (jd[:m.start()], jd[m.start():]) if m else (jd, "")
    out = {}
    for c in TERMS:
        r, n = count_term(req, c), count_term(nice, c)
        if r:
            out[c] = dict(level="must", jd_count=r + n, weight=3 if r + n >= 3 else 2)
        elif n:
            out[c] = dict(level="nice", jd_count=n, weight=1)
    return out


def extra_tokens(jd):
    """Tech-looking tokens in JD not covered by the vocabulary (review manually)."""
    cand = set(re.findall(r"\b[A-Z][a-z]+[A-Z][A-Za-z]+\b|\b[A-Za-z]+(?:\.js|\.NET|#|\+\+)\b", jd))
    known = {a.lower() for al in TERMS.values() for a in al}
    return sorted(t for t in cand if t.lower() not in known)[:25]


def run_keyword_checks(resume, jd, master):
    terms = jd_terms(jd)
    cov, ach_miss, missing = [], [], []
    for c, m in terms.items():
        inres = has_term(resume, c)
        inmas = has_term(master, c) if master else None  # None = no --master: truth unknown
        row = dict(term=c, **m, in_resume=inres, in_master=inmas)
        if inres:
            cov.append(row)
        elif inmas or inmas is None:
            ach_miss.append(row)
        else:
            missing.append(row)
    wc = sum(r["weight"] for r in cov)
    wa = sum(r["weight"] for r in ach_miss)
    ratio = wc / (wc + wa) if (wc + wa) else 1.0
    pts = round(40 * ratio, 1)
    st = "PASS" if ratio >= 0.9 else "WARN" if ratio >= 0.7 else "FAIL"
    add("K1 keyword coverage", "keywords", st, pts, 40,
        (f"{len(cov)} JD terms covered, {len(ach_miss)} in master but not in resume, "
         f"{len(missing)} Missing (not in master: do NOT add). achievable coverage {ratio:.0%}") if master is not None else
        (f"{len(cov)} JD terms covered, {len(ach_miss)} not in resume. No --master given: cannot tell which "
         f"of those are true for you; add ONLY what you really did. coverage {ratio:.0%}"))
    ex = extra_tokens(jd)
    extra = [dict(token=t, in_resume=bool(re.search(re.escape(t), resume, re.I)),
                  in_master=bool(master) and bool(re.search(re.escape(t), master, re.I))) for t in ex]
    return dict(covered=cov, add_if_true=ach_miss, missing=missing, unclassified=extra)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf")
    ap.add_argument("--jd")
    ap.add_argument("--master", help="your full fact-bank resume (markdown/text); lets the check tell 'true but missing' from 'never claim'")
    ap.add_argument("--terms", help="custom terms.json (default: terms.json next to this script)")
    ap.add_argument("--save", action="store_true", help="write ./ats-reports/<pdf-stem>-ats.json and diff vs previous run")
    ap.add_argument("--out")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.terms:
        TERMS.clear()
        TERMS.update(load_terms(a.terms))
        TERM_RES.clear()
        TERM_RES.update({c: [term_re(x) for x in al] for c, al in TERMS.items()})

    texts = extract_all(a.pdf)
    info = layout_info(a.pdf)
    run_parse_checks(texts, a.pdf)
    run_format_checks(info)
    run_text_checks(texts["pymupdf"])
    kw = None
    if a.jd:
        jd = open(a.jd, encoding="utf-8", errors="replace").read()
        if a.master and not os.path.exists(a.master):
            sys.exit(f"--master not found: {a.master}")
        master = open(a.master, encoding="utf-8").read() if a.master else None
        kw = run_keyword_checks(texts["pymupdf"], jd, master)

    got = sum(c["pts"] for c in CHECKS)
    mx = sum(c["max"] for c in CHECKS)
    score = round(100 * got / mx)
    HARD = ("P1", "P3", "F1", "F6", "F8")  # A-class: unparseable/placeholder/missing contact
    hard = [c for c in CHECKS if c["status"] == "FAIL" and (c["id"][:2] in HARD or c["id"].startswith("P2"))]
    warns = [c for c in CHECKS if c["status"] in ("WARN", "FAIL")]
    verdict = "FAIL" if hard else "PASS" if score >= PASS_SCORE else "FIX"
    rep = dict(file=os.path.basename(a.pdf), date=datetime.date.today().isoformat(), score=score,
               verdict=verdict, with_jd=bool(a.jd), checks=CHECKS, keywords=kw)

    out = a.out or (os.path.join("ats-reports", os.path.splitext(os.path.basename(a.pdf))[0] + "-ats.json")
                    if a.save else None)
    prev = None
    if out and os.path.exists(out):
        try:
            prev = json.load(open(out, encoding="utf-8"))
            if not isinstance(prev, dict) or "score" not in prev:
                prev = None
        except Exception:
            pass
    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print(f"ATS check: {rep['file']}  ({rep['date']})  JD: {'yes' if a.jd else 'no (keyword check skipped)'}")
        print(f"SCORE {score}/100  VERDICT {verdict}" + (f"  (prev {prev['score']}, {score - prev['score']:+d})" if prev else ""))
        print("-" * 78)
        for c in CHECKS:
            print(f"[{c['status']:4}] {c['id']:<22} {c['pts']:>4}/{c['max']:<3} {c['msg']}")
        if kw:
            print("-" * 78)
            f = lambda rows: ", ".join(f"{r['term']}({'must' if r['level'] == 'must' else 'nice'})" for r in rows) or "-"
            print("Covered      :", f(kw["covered"]))
            print("In master, NOT in resume (add only if TRUE + relevant):" if master is not None else "Not in resume (no --master: add only what you truly did):", f(kw["add_if_true"]))
            print("Missing (not in master; never fake):", f(kw["missing"]))
            un = [u["token"] + ("" if u["in_resume"] else " [not in resume]") for u in kw["unclassified"]]
            print("Unclassified JD tokens (review manually):", ", ".join(un) or "-")
        print("-" * 78)
        print("Heuristic only. Fix failing checks; do not chase the number. Truth > keywords.")
    if out:
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        json.dump(rep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        if not a.json:
            print(f"saved {out}")
    sys.exit({"PASS": 0, "FIX": 1, "FAIL": 2}[verdict])


if __name__ == "__main__":
    main()
