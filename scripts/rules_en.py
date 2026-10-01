"""English readability rules, tuned for English written by Korean speakers.

The failure mode here is the mirror image of the Korean one: Korean-first
drafts turn into English that is nominal, hedged, and passive because those
shapes map cleanly off Korean sentence endings. These rules catch that.
"""

import re

RULES = [
    (
        "EN-WORDY-inorder",
        "MED",
        r"\bin order to\b",
        "'in order to' is three words doing one word's job",
        "'to'",
    ),
    (
        "EN-WORDY-fact",
        "HIGH",
        r"\bthe fact that\b",
        "'the fact that' always wraps a clause that can stand alone",
        "drop it: 'the fact that X fails' -> 'X fails'",
    ),
    (
        "EN-WORDY-ability",
        "MED",
        r"\b(?:has|have|had) the ability to\b",
        "nominalised modal",
        "'can'",
    ),
    (
        "EN-WORDY-ableto",
        "MED",
        r"\bwill be able to\b",
        "future + modal + infinitive for one idea",
        "'can', or present tense",
    ),
    (
        "EN-WORDY-itis",
        "MED",
        r"\bit is (?:possible|necessary|important|required) to\b",
        "empty subject; the real subject is hiding in the infinitive",
        "name the actor: 'the worker must ...'",
    ),
    (
        "EN-WORDY-utilize",
        "LOW",
        r"\butiliz(?:e|es|ed|ing)\b",
        "'utilize' is 'use' wearing a suit",
        "'use'",
    ),
    (
        "EN-WORDY-incase",
        "MED",
        r"\bin (?:the )?case of\b",
        "usually a translated Korean conditional",
        "'if', 'when', or 'for'",
    ),
    (
        "EN-WORDY-there",
        "LOW",
        r"\bthere (?:is|are|was|were) (?:a|an|no|some|many|several)\b",
        "existential 'there' buries the subject",
        "start with the subject",
    ),
    (
        "EN-NOM-perform",
        "HIGH",
        r"\b(?:perform|conduct|carry out|execute|do)s? (?:a|an|the) \w+(?:tion|sion|ment|ing)\b",
        "verb + nominalised verb; the noun already is the action",
        "'perform a validation' -> 'validate'",
    ),
    (
        "EN-NOM-of",
        "LOW",
        r"\b\w+(?:tion|sion|ment) of the\b",
        "nominal chain",
        "turn the noun back into a verb",
    ),
    (
        "EN-PASS-by",
        "MED",
        r"\b(?:is|are|was|were|been|being) \w+(?:ed|en) by\b",
        "agentive passive; English prose reads better active",
        "put the agent first",
    ),
    (
        "EN-HEDGE-seems",
        "MED",
        r"\bit (?:seems|appears) that\b",
        "hedge with no information",
        "state it, or say what you could not verify",
    ),
    (
        "EN-HEDGE-note",
        "LOW",
        r"\b(?:please )?note that\b",
        "filler; the reader is already reading",
        "delete",
    ),
    (
        "EN-VAGUE-etc",
        "LOW",
        r"\b(?:and so on|etc\.)",
        "'etc.' asks the reader to finish your list",
        "name the rest, or say how many there are",
    ),
    (
        "EN-VAGUE-various",
        "LOW",
        r"\bvarious\b",
        "'various' is a count you did not do",
        "give the number or the names",
    ),
]

COMPILED = [(rid, sev, re.compile(pat, re.I), why, fix) for rid, sev, pat, why, fix in RULES]

# Sentence length thresholds, in words.
LONG_HIGH = 34
LONG_MED = 26
