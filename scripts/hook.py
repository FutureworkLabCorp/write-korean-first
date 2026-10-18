#!/usr/bin/env python3
"""Claude Code hooks that keep Korean replies from drifting into translationese.

A skill runs only when the model decides a task needs it, and an ordinary chat
reply never asks. These hooks put the procedure in front of every Korean turn and
check a reply after it is written. Nothing runs until the settings name this script.

    hook.py remind   UserPromptSubmit: a short reminder when the prompt is Korean
    hook.py stop     Stop: lint the reply; block once, naming the sentences to fix

The stop hook blocks on wording findings only (any HIGH, or MED_LIMIT MED), never
on length: a chat reply is long for its tables and lists, and a block that fires
on every long answer gets switched off.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lint import HANGUL, is_length, lint_text  # noqa: E402

REMINDER = """한국어로 답할 때 (write-korean-first):
- 영어로 정리한 생각을 문장째 옮기지 말고, 결론 문장부터 한국어로 쓴다.
- 독자가 아는 용어(영어, 굳은 음차어)는 그대로 둔다. 새 우리말을 지어내지 않는다.
- 고칠 것은 문장 구조다. 겹문장, '~에 대한'·'~을 통해', 주어와 서술어가 어긋난 문장."""

# A reply shorter than this is not worth a second pass.
MIN_HANGUL = 40
MED_LIMIT = 2
SHOWN = 5


def remind(event: dict) -> int:
    if HANGUL.search(event.get("prompt") or ""):
        print(REMINDER)
    return 0


def stop(event: dict) -> int:
    # Set when Claude is already continuing because of a stop hook: blocking again
    # would loop on a sentence the model judged right the first time.
    if event.get("stop_hook_active"):
        return 0
    text = event.get("last_assistant_message") or ""
    if len(HANGUL.findall(text)) < MIN_HANGUL:
        return 0

    _, findings = lint_text(text, "reply")
    flagged = []
    for f in findings:
        hits = [h for h in f["hits"] if f["lang"] == "ko" and not is_length(h) and h["severity"] != "LOW"]
        if hits:
            flagged.append((f["sentence"], hits))
    severities = [h["severity"] for _, hits in flagged for h in hits]
    if "HIGH" not in severities and severities.count("MED") < MED_LIMIT:
        return 0

    lines = []
    for sentence, hits in flagged[:SHOWN]:
        tags = ", ".join(f"{h['rule']}‹{h['match']}›" for h in hits)
        lines.append(f"- {sentence[:100]}  [{tags}] → {hits[0]['fix']}")
    reason = (
        "방금 보낸 한국어 답에서 번역투 후보가 걸렸다(write-korean-first lint).\n"
        "문맥상 고쳐야 할 문장만 고친 문장으로 짧게 다시 보여 준다. 답 전체를 다시 보내지 않는다.\n"
        "맞게 쓴 표현이면 고치지 말고 이유를 한 줄로 밝힌다.\n" + "\n".join(lines)
    )
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in ("remind", "stop"):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        # A broken event must not block the session; say why on stderr and let it through.
        print(f"write-korean-first hook: unreadable event ({e})", file=sys.stderr)
        return 0
    return remind(event) if argv[1] == "remind" else stop(event)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
