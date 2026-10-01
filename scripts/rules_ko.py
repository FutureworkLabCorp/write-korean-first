"""Korean readability rules.

Each rule is a regex over a single sentence. The point is not to be a grammar
checker -- it is to surface the sentences a human should re-read. Precision
matters more than recall here: a rule that fires on healthy prose trains the
author to ignore the whole report.
"""

import re

# (id, severity, pattern, why, fix)
RULES = [
    # --- Nominalisation: English stacks noun phrases, Korean runs on verbs. ---
    (
        "KO-NOM-about",
        "LOW",
        r"\S+에 대한 (?:검증|분석|조사|논의|처리|점검|확인|수정|평가|검토)(?:을|를|이|가|은|는|에|의|\s)",
        "명사구가 길어지면 동사로 풀 수 있다. 대상·주제를 가리키는 자연스러운 쓰임은 유지한다",
        "뜻이 같을 때만 'X에 대한 검증'을 'X를 검증'으로 바꾼다",
    ),
    (
        "KO-NOM-about2",
        "MED",
        r"\S+에 대해서?\s",
        "주제 표시가 필요할 수도 있다. 군더더기인지 문맥에서 확인한다",
        "뜻이 같으면 'X를 논의한다'처럼 줄인다",
    ),
    (
        "KO-NOM-through",
        "MED",
        r"\S+(?:을|를) 통해서?\s",
        "수단·경로를 구체적으로 쓸 수 있는지 확인한다",
        "도구면 '~로', 경로면 '~를 거쳐', 원인이면 '~라서'",
    ),
    (
        "KO-NOM-double",
        "MED",
        r"\S+(?:을|를)?\s*(?:수행|진행|실시|시행)(?:한다|합니다|했다|하고|하여|하면|할|해야)",
        "'검증을 수행한다'는 명사+빈동사다. 서술어가 두 번 나온다",
        "'검증한다' 한 단어로 줄인다",
    ),
    (
        "KO-NOM-inregard",
        "MED",
        r"에 있어서?\s",
        "'~에 있어서'는 in terms of의 직역이다",
        "'~에서', '~할 때', 또는 통째로 삭제",
    ),
    (
        "KO-NOM-genitive",
        "MED",
        r"\S+의 \S+의 ",
        "'의'가 연속되면 명사구가 3중으로 쌓인 것이다",
        "한 단계를 동사나 절로 푼다",
    ),
    (
        "KO-NOM-for",
        "LOW",
        r"\S+(?:을|를) 위한 ",
        "'~를 위한'은 for의 직역인 경우가 많다",
        "'~용', '~하는', 또는 목적절로 푼다",
    ),

    # --- Passive: Korean marks passive far less than English. ---
    (
        "KO-PASS-double",
        "HIGH",
        r"되어\s*(?:지|진|져|졌|집|짐)",
        "'되어지다'는 대개 불필요한 이중피동이다",
        "'~된다'로 충분하다",
    ),
    (
        "KO-PASS-by",
        "LOW",
        r"\S+에 의해서?\s",
        "행위자나 근거를 밝히는 표현일 수 있다. 문맥상 장황한지만 본다",
        "행위자와 초점을 유지할 수 있을 때만 능동으로 바꾼다",
    ),
    (
        "KO-PASS-verb",
        "HIGH",
        r"(?:불려|보여|쓰여|놓여|모여)(?:지|진|져|졌)",
        "이중피동이다",
        "'불린다', '보인다', '쓰인다'",
    ),

    # --- Calque: constructions that only exist because English does. ---
    (
        "KO-CAL-possible",
        "MED",
        r"(?:가능하게 한다|할 수 있도록 한다|하는 것을 가능|하는 것이 가능)",
        "가능성·능력과 실제 수행을 구분하며 간결하게 쓸 수 있는지 본다",
        "가능해진 것인지 실제 수행한 것인지 보존해 다시 쓴다",
    ),
    (
        "KO-CAL-need",
        "LOW",
        r"필요가 있다",
        "의무의 강도가 달라지지 않는 범위에서 줄일 수 있는지 본다",
        "'~해야 한다'로 바꾸면 의무가 강해질 수 있으니 문맥을 확인한다",
    ),
    (
        "KO-CAL-exist",
        "LOW",
        r"존재한다",
        "기술적 의미가 아니라면 '있다'가 더 간결할 수 있다",
        "존재 여부가 핵심이면 유지하고, 아니면 '있다'를 검토한다",
    ),
    (
        "KO-CAL-have",
        "LOW",
        r"(?:가지고 있다|가지고 있는|가진다)",
        "소유·보유를 뜻하면 자연스럽다. 장황한 경우만 본다",
        "뜻이 같으면 '~이 있다'처럼 줄인다",
    ),
    (
        "KO-CAL-saidthat",
        "LOW",
        r"(?:라고|다고) 할 수 있다",
        "가능성이나 평가의 유보를 나타낼 수 있다. 불필요한 완곡 표현인지 본다",
        "유보의 정도를 지키면서 간결하게 쓴다",
    ),
    (
        "KO-CAL-said",
        "MED",
        r"해당 \S+",
        "the said / corresponding의 습관적 직역이다",
        "'그', '이', 또는 대상 이름을 직접 쓴다",
    ),
    (
        "KO-CAL-incase",
        "LOW",
        r"\S+의 경우(?:에는|에|,|\s)(?!만)",
        "'X의 경우'는 in the case of X의 직역이다",
        "'X는', 또는 '~면'으로 조건절을 만든다",
    ),
    (
        "KO-CAL-provide",
        "LOW",
        r"제공한다",
        "provides의 기본값 번역이다",
        "실제 동작을 쓴다: '보낸다', '만든다', '연다'",
    ),

    # --- Repeated self-introductions may be redundant, not ungrammatical. ---
    (
        "KO-SUBJ-doc",
        "LOW",
        r"(?:이|본)\s*(?:문서|이슈|기능|모듈|스킬)(?:은|는)\s",
        "자연스러운 주제 표시다. 반복될 때만 군더더기인지 본다",
        "본문으로 바로 들어가도 되는지 본다",
    ),

    # --- Modifier overload: Korean resolves left-to-right; front-loading breaks it. ---
    (
        "KO-MOD-stack",
        "MED",
        r"(?:하는|되는|인|한|된|할|될|였던|했던)\s+\S+\s+(?:하는|되는|인|한|된|할|될)\s+\S+\s+(?:하는|되는|인|한|된|할|될)\s",
        "관형절이 3중이다. 서술어에 닿기 전에 독자가 기억할 게 너무 많다",
        "가장 안쪽 수식을 별도 문장으로 뺀다",
    ),
    (
        "KO-ADV-jeok",
        "LOW",
        r"\S+적(?:으로|인)\s\S*.*\S+적(?:으로|인)\s",
        "한 문장에 '~적'이 두 번 이상이면 추상도가 너무 높다",
        "구체 명사로 바꾼다",
    ),
]

COMPILED = [(rid, sev, re.compile(pat), why, fix) for rid, sev, pat, why, fix in RULES]

# --- Code-switching: an English phrase glued to a Korean particle. ---
# The most common translationese in technical docs is not a calque but an English
# noun phrase left untranslated in the middle of a Korean sentence ("source of
# truth이고", "dispatch validation failure는"). Single words are left alone: the
# glossary keeps many of them in English on purpose. Inline code is masked before
# this runs, so a symbol never reaches it.
_MIX = re.compile(
    # Words may be joined by "/" or "-", but a phrase needs a space: "user/group"
    # is a pair of alternatives, "source of truth" is an untranslated phrase.
    r"(?<![A-Za-z/-])([a-z][a-z]+(?:[/-][a-z][a-z]+)*(?: [a-z][a-z]+(?:[/-][a-z][a-z]+)*)+)"
    r"(?=(?:이고|이며|이다|이므로|이라|다|가|이|를|을|는|은|로|으로|에서|에|의|와|과|도|만"
    r"|할|하는|한다|해서|하고)(?:[\s.,)]|$))"
)
# Phrases that are terms of art in this team's writing. Extend it rather than
# arguing with the rule: a term that is always written in English is a term.
MIX_KEEP = {
    "access token", "refresh token", "event loop", "foreign key", "fail-closed",
    "fail-open", "forward-only", "rate limit", "rate limiter", "best-effort",
    "read-modify-write", "pull request", "dry-run",
}


def mixed_phrases(sentence: str):
    """English phrases glued to a Korean particle, minus the kept terms."""
    return [m.group(1) for m in _MIX.finditer(sentence) if m.group(1) not in MIX_KEEP]


_DASH = re.compile(r"\s[—–]\s")


def dash_chain(sentence: str):
    """Two or more spaced dashes: an English-style aside or a chain of clauses."""
    found = _DASH.findall(sentence)
    return ["—" * len(found)] if len(found) >= 2 else []


# (id, severity, finder, why, fix, profiles). A finder returns the matched text,
# or an empty list when the sentence is clean.
EXTRA = [
    (
        "KO-MIX",
        "MED",
        mixed_phrases,
        "영어 구를 번역하지 않고 조사를 붙였다",
        "일반 영어 구면 한국어로 쓰고, 코드면 백틱, 팀이 굳힌 용어면 MIX_KEEP에 올린다",
        ("prose",),
    ),
    (
        "KO-DASH",
        "MED",
        dash_chain,
        "대시 둘로 문장 가운데 삽입구를 끼웠거나 절을 여러 번 이었다. 한국어는 서술어가 끝에 와서 끼운 말이 어순을 끊는다",
        "삽입구는 괄호로 옮기거나 문장 뒤로 빼고, 이어 붙인 절은 첫 대시에서 나눈다",
        ("coding", "prose"),
    ),
]

# Sentence length thresholds, in characters. Measured after markdown noise,
# (in the coding profile, each English word counts as two characters -- a reader
# of a codebase takes "worker" in as one chunk, not six letters),
# parenthetical asides and wiki-link targets are removed: a `(file:line)` citation
# makes a sentence longer on screen but not harder to follow.
LONG_HIGH = 100
LONG_MED = 80
