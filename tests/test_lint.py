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
    ("사실상 같은 동작이라고 할 수 있다.", "KO-CAL-saidthat"),
    ("해당 노드를 먼저 지운다.", "KO-CAL-said"),
    ("익명 사용자의 경우 IP로 평가한다.", "KO-CAL-incase"),
    ("이 문서는 캐시 구조를 정리한다.", "KO-SUBJ-doc"),
    ("이 모듈은 재시도 기능을 제공한다.", "KO-CAL-provide"),
    ("구조적으로 보면 논리적으로 맞다.", "KO-ADV-jeok"),
    ("워크스페이스를 위한 별도 인덱스를 만든다.", "KO-NOM-for"),
    ("잡이 실패한다 — 워커가 재시도한다 — 상한에 닿으면 멈춘다.", "KO-DASH"),
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

# Fire only in the prose profile; the coding profile keeps English as written.
PROSE_ONLY = [
    ("DB 잡 큐가 상태의 source of truth이고 워커가 실행한다.", "KO-MIX"),
    ("dispatch validation failure는 제출 전에 기록된다.", "KO-MIX"),
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
    "장애 원인은 네트워크 지연인 것으로 보인다.",
    "이 PR은 권한 검사를 추가한다.",
    "이 값은 다른 값보다 더 안정적인 결과를 준다.",
    "사용자 권한에 대한 설명을 읽는다.",
    "만료된 refresh token을 다시 발급한다.",
    "캐시와 checkpoint를 함께 지운다.",
    "`job queue`가 비면 멈춘다.",
    "잡이 실패하면 워커가 재시도한다 — 상한은 3회다.",
]


def rules_fired(sentence, profile="coding"):
    lang = detect_lang(sentence)
    return {h["rule"] for h in check_sentence(sentence, lang, is_table=False, profile=profile)}


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

    for sentence, expected in PROSE_ONLY:
        if expected not in rules_fired(sentence, "prose"):
            failures.append(f"MISS  {expected} (prose): {sentence!r}")
        if expected in rules_fired(sentence):
            failures.append(f"FALSE {expected} in the default coding profile: {sentence!r}")

    # Coding profile: an English word is one chunk to the reader, not its letters.
    termy = ("worker가 queue에서 job을 꺼내 scheduler에 넘기고 timeout이 지나면 "
             "lease를 회수해 다른 worker에게 다시 맡긴다.")
    if "KO-LONG" in rules_fired(termy):
        failures.append("FALSE KO-LONG counted English letters in the coding profile")
    if "KO-LONG" not in rules_fired(termy, "prose"):
        failures.append("MISS  KO-LONG in the prose profile on the same sentence")

    # Length rules use the right unit per language.
    ko_long = "가" * 120
    if "KO-LONG" not in rules_fired(ko_long):
        failures.append("MISS  KO-LONG on a 120-char Korean sentence")
    en_long = " ".join(["word"] * 40)
    if "EN-LONG" not in rules_fired(en_long):
        failures.append("MISS  EN-LONG on a 40-word English sentence")

    # A citation in parentheses makes a sentence longer on screen, not harder to read.
    cited = "워커가 잡을 꺼내 실행하고 결과를 기록한다(" + "근거" * 40 + ")."
    if "KO-LONG" in rules_fired(cited):
        failures.append("FALSE KO-LONG counted a parenthetical aside")
    # A labelled enumeration is a list, not a sentence to split.
    listed = "재검증 범위: " + ", ".join(["상태 기계와 enum 실체"] * 8) + "."
    if "KO-LONG" in rules_fired(listed):
        failures.append("FALSE KO-LONG on a labelled enumeration")
    # ...but an unlabelled long clause still fires.
    if "KO-LONG" not in rules_fired("가" * 60 + ", " + "나" * 60 + "."):
        failures.append("MISS  KO-LONG on a long sentence with commas")

    # A wording hit outranks any length hit: it names the words to change.
    ranked = "해당 노드를 지운다.\n\n" + "가" * 130 + "."
    _, rf = lint_text(ranked, "r.md")
    if not rf or max(rf, key=lambda f: f["score"])["hits"][0]["rule"] != "KO-CAL-said":
        failures.append(f"ranking puts length above wording: {rf}")

    # Wiki links read as their label, not as "[[" noise.
    _, wl = lint_text("자세한 내용은 [[Auth-Backend-and-Local-Password-Very-Long-Page-Name-"
                      "For-Testing-Only-" + "x" * 40 + "|인증]]을 본다.", "w.md")
    if wl:
        failures.append(f"FALSE wiki-link target counted toward length: {wl}")

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

    # A soft-wrapped Markdown paragraph is one sentence with its first line.
    wrapped = "사용자 요청을 처리하는 워커가 각 작업의 상태를 확인하고\n" \
              "권한과 만료 시각을 검사한 다음 적절한 실행 경로를 선택하여\n" \
              "필요한 결과를 기록하고 호출자에게 응답을 돌려준다."
    wrapped_sentences = list(extract_sentences(wrapped))
    if len(wrapped_sentences) != 1 or wrapped_sentences[0][0] != 1:
        failures.append(f"wrapped paragraph split incorrectly: {wrapped_sentences}")
    if "KO-LONG" not in rules_fired(wrapped_sentences[0][1]):
        failures.append("MISS  KO-LONG across soft-wrapped lines")
    list_sentences = list(extract_sentences("- " + wrapped.replace("\n", "\n  ")))
    if len(list_sentences) != 1 or "KO-LONG" not in rules_fired(list_sentences[0][1]):
        failures.append(f"soft-wrapped list item split incorrectly: {list_sentences}")
    quote_sentences = list(extract_sentences("> " + wrapped.replace("\n", "\n> ")))
    if len(quote_sentences) != 1 or "KO-LONG" not in rules_fired(quote_sentences[0][1]):
        failures.append(f"soft-wrapped quote split incorrectly: {quote_sentences}")
    two_lines = list(extract_sentences("첫 문장은 여기서 끝난다.\n둘째 문장은 다음 줄에서 시작한다."))
    if [line for line, _, _ in two_lines] != [1, 2]:
        failures.append(f"sentence line mapping wrong: {two_lines}")

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
    print(f"ok — {len(POSITIVE)} positive, {len(NEGATIVE)} negative, {len(PROSE_ONLY)} prose-only, 18 structural")
    return 0


if __name__ == "__main__":
    sys.exit(main())
