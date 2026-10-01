#!/usr/bin/env python3
"""Check that a correction kept everything it must not touch.

Usage:
    check_preserve.py BEFORE AFTER [--profile coding|prose] [--json]

Exit 0 when everything is kept, 1 when something was lost, added or reshaped,
2 on an input error.

What counts as untouchable is what a reader or another document depends on by
exact text: code, links, URLs, verify comments, headings (anchors point at them),
and the shape of every table. In the coding profile, English words in prose are
kept as written too. Numbers are only reported: "5.6초" and "5.6 초" tokenise
differently, and a gate that fails on that teaches people to ignore it.

Prose inside a blockquote is not protected as a block -- a quoted status line is
still prose that may be corrected.
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

FENCE = re.compile(r"^[ \t]*(```|~~~)[^\n]*\n.*?^[ \t]*\1[ \t]*$", re.S | re.M)
INLINE = re.compile(r"`[^`\n]+`")
WIKI = re.compile(r"\[\[[^\]\n]+\]\]")
MD_TARGET = re.compile(r"\]\(([^)\s]+)[^)]*\)")
URL = re.compile(r"https?://[^\s)>\]`]+")
COMMENT = re.compile(r"<!--.*?-->", re.S)
HEADING = re.compile(r"^#{1,6}[ \t].*$", re.M)
NUM = re.compile(r"(?<![A-Za-z_\d])\d+(?:[.,:]\d+)*")
LATIN = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z][A-Za-z0-9_'-]*")

STRICT = ("code block", "inline code", "wiki link", "link target", "url", "comment",
          "heading")


def without_code(text: str) -> str:
    return INLINE.sub(" ", FENCE.sub(" ", text))


def table_shape(text: str):
    """Pipe count per table row, so a dropped column or row shows up."""
    body = FENCE.sub("", text)
    return [line.count("|") for line in body.splitlines() if line.lstrip().startswith("|")]


def inventory(text: str, profile: str):
    prose = without_code(text)
    found = {
        "code block": Counter(m.group(0) for m in FENCE.finditer(text)),
        "inline code": Counter(INLINE.findall(FENCE.sub(" ", text))),
        "wiki link": Counter(WIKI.findall(prose)),
        "link target": Counter(MD_TARGET.findall(prose)),
        "url": Counter(URL.findall(prose)),
        "comment": Counter(COMMENT.findall(prose)),
        "heading": Counter(HEADING.findall(FENCE.sub("", text))),
        "number": Counter(NUM.findall(prose)),
    }
    if profile == "coding":
        # Case-folded: moving "Durable" out of first position lowercases it, which
        # keeps the word.
        # Counted with backticks dropped but their words kept, so wrapping a word in
        # code is reported once (as inline code), not again as a lost word. Link
        # targets and one-letter tokens are not prose words.
        words = WIKI.sub(" ", COMMENT.sub(" ", URL.sub(" ", FENCE.sub(" ", text).replace("`", ""))))
        found["english word"] = Counter(w.lower() for w in LATIN.findall(words) if len(w) > 1)
    return found


def compare(before: str, after: str, profile: str):
    a, b = inventory(before, profile), inventory(after, profile)
    failures, notes = [], []
    for kind in a:
        lost, added = a[kind] - b[kind], b[kind] - a[kind]
        if not lost and not added:
            continue
        entry = {"kind": kind, "lost": sorted(lost.elements())[:8],
                 "added": sorted(added.elements())[:8]}
        if kind in STRICT:
            failures.append(entry)
        elif kind == "english word" and lost:
            # Losing an English word means it was translated; adding one is only noted.
            failures.append({**entry, "added": []})
            if added:
                notes.append({"kind": kind, "lost": [], "added": entry["added"]})
        else:
            notes.append(entry)
    if table_shape(before) != table_shape(after):
        failures.append({"kind": "table shape", "lost": [], "added": []})
    return failures, notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--profile", choices=("coding", "prose"), default="coding")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    try:
        before = Path(args.before).read_text(encoding="utf-8")
        after = Path(args.after).read_text(encoding="utf-8")
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    failures, notes = compare(before, after, args.profile)
    if args.json:
        json.dump({"pass": not failures, "failures": failures, "notes": notes},
                  sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        print("PASS" if not failures else f"FAIL ({len(failures)})")
        for f in failures:
            print(f"  {f['kind']}: lost {f['lost']} added {f['added']}")
        for n in notes:
            print(f"  (참고) {n['kind']}: lost {n['lost']} added {n['added']}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
