#!/usr/bin/env python3
"""Regression tests for the readability lint.

Run standalone (no repo fixtures, no DB):
    python3 tests/test_lint.py

Each case pins one rule. The NEGATIVE cases matter more than the positive
ones: a rule that fires on healthy prose trains the author to ignore the
whole report, which is worse than missing a finding.
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from lint import check_sentence, detect_lang, extract_sentences, lint_text  # noqa: E402

# (sentence, rule id that must fire)
POSITIVE = [
    ("사용자 권한에 대한 검증을 먼저 한다.", "KO-NOM-about"),
    ("이 값에 대해 논의한 적이 있다.", "KO-NOM-about2"),
    ("워커를 통해 작업을 넘긴다.", "KO-NOM-through"),
    ("입력값 검증을 수행한다.", "KO-NOM-double"),
    ("성능에 있어서 차이가 없다.", "KO-NOM-inregard"),
    ("서버의 캐시의 만료 시각을 읽는다.", "KO-NOM-genitive"),
    ("이 값은 매번 갱신되어진다.", "KO-PASS-double"),
    ("토큰은 스케줄러에 의해 발급된다.", "KO-PASS-by"),
    ("그 이름으로 불려진다.", "KO-PASS-verb"),
    ("이 설정이 병렬 실행을 가능하게 한다.", "KO-CAL-possible"),
    ("인덱스를 다시 만들 필요가 있다.", "KO-CAL-need"),
    ("같은 이름의 노드가 존재한다.", "KO-CAL-exist"),
    ("이 객체는 세션을 가지고 있다.", "KO-CAL-have"),
    ("타임아웃이 원인인 것으로 보인다.", "KO-CAL-seem"),
    ("사실상 같은 동작이라고 할 수 있다.", "KO-CAL-saidthat"),
    ("해당 노드를 먼저 지운다.", "KO-CAL-said"),
    ("익명 사용자의 경우 IP로 평가한다.", "KO-CAL-incase"),
    ("이 PR은 만료 처리를 고친다.", "KO-SUBJ-change"),
    ("이 문서는 캐시 구조를 정리한다.", "KO-SUBJ-doc"),
    ("이 값은 다른 값보다 더 안정적인 결과를 준다.", "KO-CAL-more"),
    ("이 모듈은 재시도 기능을 제공한다.", "KO-CAL-provide"),
    ("구조적으로 보면 논리적으로 맞다.", "KO-ADV-jeok"),
    ("워크스페이스를 위한 별도 인덱스를 만든다.", "KO-NOM-for"),
    ("The worker will perform a validation of the payload.", "EN-NOM-perform"),
    ("In order to retry, set the flag.", "EN-WORDY-inorder"),
    ("The fact that it fails is known.", "EN-WORDY-fact"),
    ("It is necessary to flush the cache.", "EN-WORDY-itis"),
    ("The job is handled by the scheduler.", "EN-PASS-by"),
    ("It seems that the token expired.", "EN-HEDGE-seems"),
    ("We utilize a retry loop.", "EN-WORDY-utilize"),
    ("This covers timeouts, retries, and so on.", "EN-VAGUE-etc"),
    ("The node has the ability to retry.", "EN-WORDY-ability"),
]

# Healthy prose that must stay silent.
NEGATIVE = [
    "스케줄러가 매 실행마다 토큰을 갱신한다.",
    "캐시가 무효화되면 워커가 다시 만든다.",
    "인증 사용자는 user/group으로 평가한다.",
    "관리자만 로그인할 수 있다.",
    "이 조건에서만 재시도한다.",
    "노드를 지우고 관계를 다시 잇는다.",
    "The scheduler refreshes the token on every run.",
    "The worker rebuilds the cache after invalidation.",
    "Only admins can sign in.",
]


def rules_fired(sentence):
    lang = detect_lang(sentence)
    return {h["rule"] for h in check_sentence(sentence, lang, is_table=False)}


def main() -> int:
    failures = []

    for sentence, expected in POSITIVE:
        fired = rules_fired(sentence)
        if expected not in fired:
            failures.append(f"MISS  {expected}: {sentence!r} -> {sorted(fired) or 'nothing'}")

    for sentence in NEGATIVE:
        fired = rules_fired(sentence)
        if fired:
            failures.append(f"FALSE {sorted(fired)}: {sentence!r}")

    # Length rules use the right unit per language.
    ko_long = "가" * 120
    if "KO-LONG" not in rules_fired(ko_long):
        failures.append("MISS  KO-LONG on a 120-char Korean sentence")
    en_long = " ".join(["word"] * 40)
    if "EN-LONG" not in rules_fired(en_long):
        failures.append("MISS  EN-LONG on a 40-word English sentence")

    # Markdown scaffolding must not reach the rules.
    md = """---
title: 이것에 대한 문서
---

```python
x = "이 값에 대한 처리를 수행한다"
```

<!-- 이 주석에 대한 처리를 수행한다 -->

본문은 짧게 쓴다.
"""
    _, findings = lint_text(md, "t.md")
    if findings:
        failures.append(f"FALSE frontmatter/fence/comment leaked: {findings}")

    # lint-skip markers let a doc quote bad prose without tripping rules.
    skipped = """검증을 수행한다. <!-- lint-skip -->

<!-- lint-skip-start -->
이 값은 갱신되어진다.
스케줄러에 의해 발급된다.
<!-- lint-skip-end -->

여기는 다시 검사한다: 토큰을 발급할 필요가 있다.
"""
    _, sk = lint_text(skipped, "s.md")
    fired = {h["rule"] for f in sk for h in f["hits"]}
    if fired != {"KO-CAL-need"}:
        failures.append(f"lint-skip wrong: {sorted(fired)}")

    # Inline code is masked, so a symbol name never trips a rule.
    if rules_fired("`get_data_by_id`로 읽는다."):
        failures.append("FALSE inline code tripped a rule")

    # Line numbers survive preprocessing.
    lines = "\n".join(["# 제목", "", "첫 문단이다.", "", "둘째 문단이다."])
    nums = [ln for ln, _, _ in extract_sentences(lines)]
    if 5 not in nums:
        failures.append(f"line numbers wrong: {nums}")

    # A typo in a gate path must not report success.
    lint_cli = Path(__file__).resolve().parent.parent / "scripts" / "lint.py"
    missing = subprocess.run(
        [sys.executable, str(lint_cli), "__definitely_missing__"],
        capture_output=True,
        text=True,
        check=False,
    )
    if missing.returncode != 2:
        failures.append(f"missing input returned {missing.returncode}, expected 2")

    if failures:
        print(f"FAIL ({len(failures)})")
        for f in failures:
            print("  " + f)
        return 1
    print(f"ok — {len(POSITIVE)} positive, {len(NEGATIVE)} negative, 7 structural")
    return 0


if __name__ == "__main__":
    sys.exit(main())
