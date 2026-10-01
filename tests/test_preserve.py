#!/usr/bin/env python3
"""Regression tests for the preservation gate.

Run standalone:
    python3 tests/test_preserve.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_preserve import compare  # noqa: E402

BASE = """# 제목

## 2. 흐름

Retry queue가 실패한 delivery의 source of truth이고, `dispatch()`가 꺼낸다([[Notification-Dispatch]]).
<!-- verify: anchor src/app/x.py:10 "def dispatch" -->

> 상태: 5.6초 안에 끝난다.

| a | b |
|---|---|
| 1 | 2 |

```python
x = 1
```
"""


def kinds(after, profile="coding"):
    failures, _ = compare(BASE, after, profile)
    return {f["kind"] for f in failures}


CASES = [
    # (description, edited text, kinds that must fail)
    ("unchanged", BASE, set()),
    ("Korean around English reworded", BASE.replace(
        "Retry queue가 실패한 delivery의 source of truth이고,",
        "실패한 delivery의 source of truth는 Retry queue이고,"), set()),
    ("sentence-initial English lowercased", BASE.replace(
        "Retry queue가 실패한 delivery의 source of truth이고,",
        "실패한 delivery의 source of truth는 retry queue이고,"), set()),
    ("quoted prose corrected", BASE.replace("5.6초 안에 끝난다", "5.6초 안에 마친다"), set()),
    ("heading reworded", BASE.replace("## 2. 흐름", "## 2. 처리 흐름"), {"heading"}),
    ("English translated", BASE.replace("source of truth", "기준"), {"english word"}),
    ("backticks added", BASE.replace("실패한 delivery", "실패한 `delivery`"), {"inline code"}),
    ("inline code edited", BASE.replace("`dispatch()`", "`dispatch`"), {"inline code"}),
    ("wiki link dropped", BASE.replace("([[Notification-Dispatch]])", ""), {"wiki link"}),
    ("verify comment dropped", BASE.replace(
        '<!-- verify: anchor src/app/x.py:10 "def dispatch" -->\n', ""), {"comment"}),
    ("table column dropped", BASE.replace("| a | b |\n|---|---|\n| 1 | 2 |",
                                          "| a |\n|---|\n| 1 |"), {"table shape"}),
    ("code block edited", BASE.replace("x = 1", "x = 2"), {"code block"}),
]


def main() -> int:
    failures = []
    for desc, after, expected in CASES:
        got = kinds(after)
        if got != expected:
            failures.append(f"{desc}: expected {sorted(expected)}, got {sorted(got)}")
    if "english word" in kinds(BASE.replace("source of truth", "기준"), "prose"):
        failures.append("prose profile must not guard English words")

    # A new "commonly / generally" claim is noted, never failed.
    claimed = BASE.replace("5.6초 안에 끝난다", "일반적으로 5.6초 안에 끝난다")
    fails, notes = compare(BASE, claimed, "coding")
    if fails or not any(n["kind"] == "new general claim" for n in notes):
        failures.append(f"new general claim not noted: {fails} {notes}")
    # A wholesale rewrite is noted by change rate.
    _, notes = compare(BASE, BASE.replace("실패한 delivery의 source of truth이고",
                                          "x" * 400), "coding")
    if not any(n["kind"].startswith("change rate") for n in notes):
        failures.append("large rewrite not noted by change rate")
    if failures:
        print(f"FAIL ({len(failures)})")
        for f in failures:
            print("  " + f)
        return 1
    print(f"ok — {len(CASES) + 3} cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
