#!/usr/bin/env python3
"""Render a resume markdown file to a single-column, text-selectable PDF (PyMuPDF Story).

usage: build_pdf.py INPUT.md OUTPUT.pdf [compact|fit]
  fit = shrink font (9.6 -> 8.8pt) until the resume fits ONE page.
Built-in font only. Ligatures are suppressed in inline() (empty span after f); system TTFs were tested and corrupt hyphens/spaces in the text layer.
Stops at the first '## Maintainer notes' / '## Editor notes' section and drops the banner above the first '---'.
"""
import html
import os
import re
import sys

import fitz  # PyMuPDF

ACCENT = "#1F4E79"  # single dark-blue accent: name + section headings only
CSS_TMPL = """
body { font-family: FONTFAMILY; font-size: %(fs)spt; line-height: %(lh)s; color: #111; }
h1 { font-size: 20pt; margin: 0 0 1pt 0; letter-spacing: 0.5pt; color: ACCENT; }
h2 { font-size: 10.5pt; margin: %(h2m)spt 0 2pt 0; border-bottom: 0.9pt solid ACCENT; color: ACCENT; padding-bottom: 1pt; text-transform: uppercase; letter-spacing: 0.6pt; }
p { margin: 1.5pt 0; }
ul { margin: 1pt 0 2pt 0; padding-left: 13pt; }
li { margin: %(lim)spt 0; }
.role { margin-top: 5pt; }
"""
SIZES = {"normal": dict(fs="9.6", lh="1.28", h2m="9", lim="1.2"),
         "compact": dict(fs="9", lh="1.2", h2m="6", lim="0.6")}


def inline(text):
    t = html.escape(text, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", t)
    t = re.sub(r"`(.+?)`", r"\1", t)
    # empty inline span between f and i/l/f stops ligature shaping (U+FB01/FB02 break ATS keyword match)
    return re.sub(r"f(?=[ilf])", "f<span></span>", t)


def convert(md):
    lines = md.splitlines()
    # drop banner: everything before the first '---' line
    if "---" in [l.strip() for l in lines]:
        lines = lines[[l.strip() for l in lines].index("---") + 1:]
    out, in_list = [], False
    for raw in lines:
        l = raw.rstrip()
        if re.match(r"^## (Maintainer|Editor) notes", l):
            break
        if l.strip() == "---":
            break
        if l.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline(l[2:])}</li>")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        if not l.strip():
            continue
        if l.startswith("# "):
            out.append(f"<h1>{inline(l[2:])}</h1>")
        elif l.startswith("## "):
            out.append(f"<h2>{inline(l[3:])}</h2>")
        elif re.match(r"^\*\*.+\*\*", l) and "—" in l:
            out.append(f'<p class="role">{inline(l)}</p>')
        else:
            out.append(f"<p>{inline(l)}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


FONTS = "C:/Windows/Fonts"
FACES = """
@font-face { font-family: ar; src: url(arial.ttf); }
@font-face { font-family: ar; font-weight: bold; src: url(arialbd.ttf); }
@font-face { font-family: ar; font-style: italic; src: url(ariali.ttf); }
@font-face { font-family: ar; font-weight: bold; font-style: italic; src: url(arialbi.ttf); }
"""


def render(body, css, out, archive):
    story = fitz.Story(html=f"<body>{body}</body>", user_css=css, archive=archive)
    mediabox = fitz.paper_rect("letter")
    where = mediabox + (40, 36, -40, -36)
    writer = fitz.DocumentWriter(out)
    more, pages = 1, 0
    while more:
        dev = writer.begin_page(mediabox)
        more, _ = story.place(where)
        story.draw(dev)
        writer.end_page()
        pages += 1
    writer.close()
    return pages


def main():
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    mode = sys.argv[3] if len(sys.argv) == 4 else "normal"
    have_arial = False  # system TTFs (Arial, Tahoma, ...) break hyphen/space extraction (U+00AD, NBSP); built-in Nimbus Sans is clean
    family, faces, archive = ("ar, sans-serif", FACES, fitz.Archive(FONTS)) if have_arial else ("sans-serif", "", None)
    md = open(sys.argv[1], encoding="utf-8").read()
    body = convert(md)
    sizes = [dict(SIZES["compact"] if mode == "compact" else SIZES["normal"])]
    if mode == "fit":
        sizes = [dict(SIZES["normal"], fs=f"{x / 10:.1f}") for x in range(96, 87, -2)]
    for sz in sizes:
        css = faces + (CSS_TMPL % sz).replace("ACCENT", ACCENT).replace("FONTFAMILY", family)
        pages = render(body, css, sys.argv[2], archive)
        if mode != "fit" or pages == 1:
            break
    print(f"wrote {sys.argv[2]} ({pages} page(s), font {sz['fs']}pt, {'Arial' if have_arial else 'sans-serif'})")


if __name__ == "__main__":
    main()
