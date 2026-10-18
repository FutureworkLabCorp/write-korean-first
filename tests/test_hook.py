#!/usr/bin/env python3
"""Regression tests for the Claude Code hooks.

Run standalone:
    python3 tests/test_hook.py

Each case feeds the hook the JSON event Claude Code sends on stdin and checks what
it prints. A hook that blocks a healthy reply is worse than one that misses a bad
one: the first gets the hook switched off.
"""

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "scripts" / "hook.py"

CLEAN = (
    "워크스페이스를 지우면 문서도 함께 사라진다. 복구는 30일 안에만 된다. "
    "그 뒤에는 원본 파일까지 지운다. 핸들러가 예외를 삼켜도 잡이 다시 돈다."
)
STIFF = (
    "이 작업에 대해 먼저 논의한 뒤 입력값 검증을 수행한다. 워커를 통해 결과를 넘긴다. "
    "그 다음 관리자 권한을 필요로 하는 단계가 남는다."
)


def run(mode, event, raw=None):
    proc = subprocess.run(
        [sys.executable, str(HOOK), *mode],
        input=raw if raw is not None else json.dumps(event, ensure_ascii=False),
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout.strip()


def main() -> int:
    failures = []

    code, out = run(["stop"], {"last_assistant_message": STIFF, "stop_hook_active": False})
    try:
        decision = json.loads(out) if out else {}
    except json.JSONDecodeError:
        decision = {}
    if code != 0 or decision.get("decision") != "block" or "KO-NOM-double" not in decision.get("reason", ""):
        failures.append(f"stiff reply was not blocked: {code} {out!r}")

    code, out = run(["stop"], {"last_assistant_message": STIFF, "stop_hook_active": True})
    if out:
        failures.append(f"blocked again while already continuing: {out!r}")

    code, out = run(["stop"], {"last_assistant_message": CLEAN})
    if out:
        failures.append(f"blocked a healthy reply that keeps team jargon: {out!r}")

    english = "The worker will perform a validation of the payload in order to retry. " * 3
    code, out = run(["stop"], {"last_assistant_message": english})
    if out:
        failures.append(f"blocked an English reply: {out!r}")

    code, out = run(["stop"], {"last_assistant_message": "검증을 수행한다."})
    if out:
        failures.append(f"blocked a reply too short to judge: {out!r}")

    long_clean = ("워커가 잡을 꺼내 실행하고 결과를 기록한 다음 호출자에게 응답을 돌려주며 "
                  "실패하면 같은 잡을 다시 큐에 넣어 상한에 닿을 때까지 재시도한다. ") * 3
    code, out = run(["stop"], {"last_assistant_message": long_clean})
    if out:
        failures.append(f"blocked on length alone: {out!r}")

    code, out = run(["remind"], {"prompt": "아카이브 테이블은 꼭 필요해?"})
    if "write-korean-first" not in out:
        failures.append(f"no reminder on a Korean prompt: {out!r}")

    code, out = run(["remind"], {"prompt": "Is the archive table required?"})
    if out:
        failures.append(f"reminder on an English prompt: {out!r}")

    code, out = run(["stop"], None, raw="{not json")
    if code != 0 or out:
        failures.append(f"malformed event was not let through: {code} {out!r}")

    code, out = run(["nope"], {})
    if code != 2:
        failures.append(f"unknown mode returned {code}, expected 2")

    if failures:
        print(f"FAIL ({len(failures)})")
        for f in failures:
            print("  " + f)
        return 1
    print("ok — 10 cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
