"""
Détection centralisée des questions dans les réponses agents.
"""
from __future__ import annotations

import re
from typing import List, Tuple

QUESTION_WORDS = {
    "qui",
    "que",
    "quoi",
    "quel",
    "quelle",
    "quels",
    "quelles",
    "comment",
    "où",
    "ou",
    "quand",
    "pourquoi",
    "combien",
    "lequel",
    "laquelle",
    "lesquels",
    "lesquelles",
}

QUESTION_REGEX_PATTERNS = [
    (re.compile(r"\b(pouvez|pourriez|peux|pourrais|voudriez)\s+(?:vous|tu)\b", re.IGNORECASE), "polite_request"),
    (re.compile(r"\b(est[-\s]?ce que)\b", re.IGNORECASE), "est_ce_que"),
    (re.compile(r"\bj[' ]?aurais(?: juste)? besoin\b", re.IGNORECASE), "aurais_besoin"),
    (re.compile(r"\bj[' ]?ai besoin\b", re.IGNORECASE), "jai_besoin"),
    (re.compile(r"\b(peux|pourrais)[-\s]?tu\b", re.IGNORECASE), "tu_request"),
    (re.compile(r"\bserait[-\s]?il possible\b", re.IGNORECASE), "serait_il_possible"),
    (re.compile(r"\bpourriez[-\s]?vous\b", re.IGNORECASE), "pourriez_vous"),
]


def detect_questions(text: str) -> Tuple[bool, List[str]]:
    """
    Détecte si un texte contient des questions en se basant sur les marqueurs
    de ponctuation, les formes interrogatives et les mots introducteurs.
    """
    matches: List[str] = []
    if "?" in text:
        matches.append("question_mark")

    normalized = text.lower()
    for pattern, label in QUESTION_REGEX_PATTERNS:
        if pattern.search(normalized):
            matches.append(label)

    # Analyse des phrases pour détecter les mots interrogatifs en tête
    sentences = re.split(r"[.!?\n]", text)
    for sentence in sentences:
        stripped = sentence.strip()
        if not stripped:
            continue
        first_word = re.split(r"[^\wÀ-ÿ']+", stripped)[0].lower()
        if first_word in QUESTION_WORDS:
            matches.append(f"question_word:{first_word}")

    return (len(matches) > 0, matches)

