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
        "HIGH",
        r"\S+에 대한 ",
        "'A에 대한 B'는 영어 of/about 구문을 명사로 쌓은 것이다",
        "조사로 흡수한다: 'X에 대한 검증' -> 'X를 검증'",
    ),
    (
        "KO-NOM-about2",
        "MED",
        r"\S+에 대해서?\s",
        "'~에 대해'도 같은 명사 쌓기다",
        "'X에 대해 논의한다' -> 'X를 논의한다'",
    ),
    (
        "KO-NOM-through",
        "MED",
        r"\S+(?:을|를) 통해서?\s",
        "'~을 통해'는 through의 기계 번역이다",
        "도구면 '~로', 경로면 '~를 거쳐', 원인이면 '~라서'",
    ),
    (
        "KO-NOM-double",
        "HIGH",
        r"\S+(?:을|를)?\s*(?:수행|진행|실시|시행)(?:한다|합니다|했다|하고|하여|하면|할|해야)",
        "'검증을 수행한다'는 명사+빈동사다. 서술어가 두 번 나온다",
        "'검증한다' 한 단어로 줄인다",
    ),
    (
        "KO-NOM-inregard",
        "HIGH",
        r"에 있어서?\s",
        "'~에 있어서'는 in terms of의 직역이다",
        "'~에서', '~할 때', 또는 통째로 삭제",
    ),
    (
        "KO-NOM-genitive",
        "HIGH",
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
        "'되어지다'는 이중피동이다. 문법적으로도 틀렸다",
        "'~된다'로 충분하다",
    ),
    (
        "KO-PASS-by",
        "HIGH",
        r"\S+에 의해서?\s",
        "'~에 의해'는 by 수동태의 직역이다",
        "능동으로 뒤집는다. 행위자가 안 떠오르면 그게 진짜 문제다",
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
        "HIGH",
        r"(?:가능하게 한다|할 수 있도록 한다|하는 것을 가능|하는 것이 가능)",
        "enable/make it possible의 직역이다",
        "'~한다', '~할 수 있다'로 직접 쓴다",
    ),
    (
        "KO-CAL-need",
        "HIGH",
        r"필요가 있다",
        "there is a need to의 직역이다",
        "'~해야 한다'",
    ),
    (
        "KO-CAL-exist",
        "MED",
        r"존재한다",
        "exists를 그대로 옮긴 것이다",
        "'있다'",
    ),
    (
        "KO-CAL-have",
        "MED",
        r"(?:가지고 있다|가지고 있는|가진다)",
        "has의 직역이다",
        "'~이 있다', 또는 소유격으로",
    ),
    (
        "KO-CAL-seem",
        "MED",
        r"것으로 (?:보인다|생각된다|판단된다|예상된다)",
        "it seems that의 직역이자 책임 회피다",
        "확인했으면 단정하고, 아니면 '확인 못 했다'고 쓴다",
    ),
    (
        "KO-CAL-saidthat",
        "MED",
        r"(?:라고|다고) 할 수 있다",
        "it can be said that의 직역이다. 아무 정보도 더하지 않는다",
        "그냥 단정한다",
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
        "KO-CAL-more",
        "LOW",
        r"보다 (?:더 )?\S+(?:한|인|적인)\s",
        "비교 대상 없는 'more X'의 직역이다",
        "무엇보다 더인지 쓰거나, '보다'를 뺀다",
    ),
    (
        "KO-CAL-provide",
        "LOW",
        r"제공한다",
        "provides의 기본값 번역이다",
        "실제 동작을 쓴다: '보낸다', '만든다', '연다'",
    ),

    # --- Inanimate subject: English lets documents act; Korean does not. ---
    (
        "KO-SUBJ-change",
        "MED",
        r"(?:이|본)\s*(?:PR|커밋|변경사항|변경|패치|작업)(?:은|는|이|가)\s",
        "'이 PR은 ~한다'는 This PR does의 직역이다. 한국어에서 PR은 행위자가 아니다",
        "한 일을 쓴다: '~하도록 고쳤다', '~를 추가했다'",
    ),
    (
        "KO-SUBJ-doc",
        "LOW",
        r"(?:이|본)\s*(?:문서|이슈|기능|모듈|스킬)(?:은|는)\s",
        "문서가 스스로를 소개하는 관용구다. 한 번은 괜찮고 반복되면 군더더기다",
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

# Sentence length thresholds, in characters (excluding markdown noise).
LONG_HIGH = 100
LONG_MED = 80
