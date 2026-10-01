#!/usr/bin/env python3
"""Deterministic readability lint for Korean and English prose.

Usage:
    lint.py FILE [FILE ...]          # report
    lint.py -                        # read from stdin
    lint.py --json FILE              # machine-readable
    lint.py --gate --max-rate 0.15 FILE   # exit 1 when over budget

The lint never rewrites. It marks the sentences a human (or the model) must
re-read, ranked so the worst ones come first. Rules live in rules_ko.py and
rules_en.py; see reference/why-translationese.md for the reasoning behind them.
"""

import argparse
from bisect import bisect_right
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import rules_en  # noqa: E402
import rules_ko  # noqa: E402

SEV_WEIGHT = {"HIGH": 3, "MED": 2, "LOW": 1}
HANGUL = re.compile(r"[가-힣]")

_FENCE = re.compile(r"^\s*(?:```|~~~)")
_INLINE_CODE = re.compile(r"`[^`]*`")
_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_URL = re.compile(r"https?://\S+")
_LEAD = re.compile(r"^\s*(?:[>#]+\s*|[-*+]\s+|\d+[.)]\s+|\[[ xX]\]\s*)+")
_EMPHASIS = re.compile(r"[*_]{1,3}([^*_]+)[*_]{1,3}")
_HTML_COMMENT_OPEN = re.compile(r"<!--")
# Documents that quote bad prose as an example need a way to opt out.
_SKIP_START = re.compile(r"<!--\s*lint-skip-start\s*-->")
_SKIP_END = re.compile(r"<!--\s*lint-skip-end\s*-->")
_SKIP_LINE = re.compile(r"<!--\s*lint-skip\s*-->")
_HTML_COMMENT_CLOSE = re.compile(r"-->")
# Sentence break: after a terminal mark, before something that starts a clause.
_SENT = re.compile(r"(?<=[.!?])\s+(?=[가-힣A-Z(\[`])|(?<=[가-힣][.])\s+")


def clean_line(line: str) -> str:
    """Strip markdown scaffolding so rules see prose, not syntax."""
    line = _MD_IMAGE.sub("", line)
    line = _MD_LINK.sub(r"\1", line)
    line = _URL.sub("", line)
    line = _INLINE_CODE.sub("CODE", line)
    line = _LEAD.sub("", line)
    line = _EMPHASIS.sub(r"\1", line)
    return line.strip()


def extract_sentences(text: str):
    """Yield (line_no, sentence, is_table_cell) for every prose sentence."""
    in_fence = False
    in_comment = False
    in_skip = False
    lines = text.splitlines()

    # Skip a leading YAML frontmatter block.
    start = 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                start = i + 1
                break

    paragraph = []
    in_quote = False

    def flush():
        nonlocal paragraph
        starts, numbers, parts = [], [], []
        offset = 0
        for lineno, part in paragraph:
            starts.append(offset)
            numbers.append(lineno)
            parts.append(part)
            offset += len(part) + 1
        joined = " ".join(parts)
        result = []
        start = 0
        for boundary in list(_SENT.finditer(joined)) + [None]:
            end = boundary.start() if boundary else len(joined)
            sent = joined[start:end].strip()
            if len(sent) >= 8:
                line = numbers[bisect_right(starts, start) - 1]
                result.append((line, sent, False))
            start = boundary.end() if boundary else len(joined)
        paragraph = []
        return result

    for idx in range(start, len(lines)):
        raw = lines[idx]
        lineno = idx + 1

        if _SKIP_START.search(raw):
            yield from flush()
            in_quote = False
            in_skip = True
            continue
        if _SKIP_END.search(raw):
            in_skip = False
            continue
        if in_skip or _SKIP_LINE.search(raw):
            yield from flush()
            in_quote = False
            continue

        if _FENCE.match(raw):
            yield from flush()
            in_quote = False
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        if in_comment:
            if _HTML_COMMENT_CLOSE.search(raw):
                in_comment = False
            continue
        if _HTML_COMMENT_OPEN.search(raw) and not _HTML_COMMENT_CLOSE.search(raw):
            yield from flush()
            in_quote = False
            in_comment = True
            continue
        raw = re.sub(r"<!--.*?-->", "", raw)

        stripped = raw.strip()
        if not stripped or set(stripped) <= set("-=|: "):
            yield from flush()
            in_quote = False
            continue

        is_table = stripped.startswith("|")
        is_block = bool(_LEAD.match(raw))
        is_quote = stripped.startswith(">")
        is_heading = stripped.startswith("#")
        if is_table or is_heading or (is_block and not is_quote) or (is_quote != in_quote):
            yield from flush()
        in_quote = is_quote
        chunks = [c for c in stripped.strip("|").split("|")] if is_table else [stripped]

        for chunk in chunks:
            cleaned = clean_line(chunk)
            if len(cleaned) < 8:
                continue
            if is_table:
                for sent in _SENT.split(cleaned):
                    if len(sent.strip()) >= 8:
                        yield lineno, sent.strip(), True
            else:
                paragraph.append((lineno, cleaned))
        if is_heading:
            yield from flush()
    yield from flush()


def detect_lang(sentence: str) -> str:
    letters = [c for c in sentence if c.isalpha()]
    if not letters:
        return "none"
    hangul = sum(1 for c in letters if HANGUL.match(c))
    return "ko" if hangul / len(letters) >= 0.15 else "en"


def check_sentence(sentence: str, lang: str, is_table: bool):
    """Return a list of findings for one sentence."""
    mod = rules_ko if lang == "ko" else rules_en
    out = []

    for rid, sev, pat, why, fix in mod.COMPILED:
        m = pat.search(sentence)
        if m:
            out.append({"rule": rid, "severity": sev, "why": why, "fix": fix,
                        "match": m.group(0).strip()})

    if not is_table:
        size = len(sentence) if lang == "ko" else len(sentence.split())
        hi, med = mod.LONG_HIGH, mod.LONG_MED
        unit = "자" if lang == "ko" else "words"
        if size > hi:
            out.append({"rule": f"{lang.upper()}-LONG", "severity": "HIGH",
                        "why": f"{size}{unit} — 한 호흡에 안 읽힌다"
                               if lang == "ko" else f"{size} {unit} in one sentence",
                        "fix": "서술어를 기준으로 둘로 쪼갠다" if lang == "ko"
                               else "split at the main verb", "match": ""})
        elif size > med:
            out.append({"rule": f"{lang.upper()}-LONG", "severity": "MED",
                        "why": f"{size}{unit}", "fix": "쪼갤 자리가 있는지 본다"
                        if lang == "ko" else "look for a split point", "match": ""})
    return out


def lint_text(text: str, source: str):
    sentences, findings = 0, []
    for lineno, sent, is_table in extract_sentences(text):
        lang = detect_lang(sent)
        if lang == "none":
            continue
        sentences += 1
        hits = check_sentence(sent, lang, is_table)
        if hits:
            score = sum(SEV_WEIGHT[h["severity"]] for h in hits)
            findings.append({"file": source, "line": lineno, "lang": lang,
                             "sentence": sent, "score": score, "hits": hits})
    return sentences, findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help="markdown/text files, or - for stdin")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--top", type=int, default=15, help="rewrite candidates to show")
    ap.add_argument("--min-severity", choices=["LOW", "MED", "HIGH"], default="LOW")
    ap.add_argument("--gate", action="store_true", help="exit 1 when over budget")
    ap.add_argument("--max-rate", type=float, default=0.15,
                    help="max share of flagged sentences (gate mode)")
    ap.add_argument("--max-high", type=int, default=0,
                    help="max HIGH findings allowed (gate mode)")
    args = ap.parse_args()

    floor = SEV_WEIGHT[args.min_severity]
    total_sent, all_findings = 0, []
    input_error = False

    for p in args.paths:
        if p == "-":
            text, name = sys.stdin.read(), "<stdin>"
        else:
            path = Path(p)
            if not path.is_file():
                print(f"error (not a file): {p}", file=sys.stderr)
                input_error = True
                continue
            text, name = path.read_text(encoding="utf-8", errors="replace"), p
        n, f = lint_text(text, name)
        total_sent += n
        all_findings.extend(f)

    for f in all_findings:
        f["hits"] = [h for h in f["hits"] if SEV_WEIGHT[h["severity"]] >= floor]
    all_findings = [f for f in all_findings if f["hits"]]
    for f in all_findings:
        f["score"] = sum(SEV_WEIGHT[h["severity"]] for h in f["hits"])

    all_findings.sort(key=lambda f: (-f["score"], f["file"], f["line"]))
    high = sum(1 for f in all_findings for h in f["hits"] if h["severity"] == "HIGH")
    rate = len(all_findings) / total_sent if total_sent else 0.0

    by_rule = {}
    for f in all_findings:
        for h in f["hits"]:
            by_rule[h["rule"]] = by_rule.get(h["rule"], 0) + 1

    if args.json:
        json.dump({"sentences": total_sent, "flagged": len(all_findings),
                   "rate": round(rate, 4), "high": high, "by_rule": by_rule,
                   "findings": all_findings[: args.top]},
                  sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        long_n = by_rule.get("KO-LONG", 0) + by_rule.get("EN-LONG", 0)
        patt_n = sum(by_rule.values()) - long_n
        print(f"문장 {total_sent} · 지적 {len(all_findings)}"
              f" ({rate:.1%}) · HIGH {high}")
        print(f"  길이 {long_n} · 번역투 패턴 {patt_n}")
        if by_rule:
            print("\n규칙별:")
            for rid, n in sorted(by_rule.items(), key=lambda kv: -kv[1]):
                print(f"  {n:4d}  {rid}")
        if all_findings:
            print(f"\n재작성 우선순위 (상위 {min(args.top, len(all_findings))}):")
            for f in all_findings[: args.top]:
                print(f"\n  {f['file']}:{f['line']}  [score {f['score']}]")
                print(f"    {f['sentence'][:160]}")
                for h in f["hits"]:
                    tag = f"{h['severity']:4s} {h['rule']}"
                    hit = f" ‹{h['match']}›" if h["match"] else ""
                    print(f"      {tag}{hit}")
                    print(f"        왜: {h['why']}")
                    print(f"        →  {h['fix']}")

    if input_error:
        return 2
    if args.gate and (rate > args.max_rate or high > args.max_high):
        print(f"\nGATE FAIL: rate {rate:.1%} > {args.max_rate:.0%}"
              f" or HIGH {high} > {args.max_high}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
