"""Course normalization + smart matching for import-time deduplication.

This module is intentionally lightweight and rule-based so we can improve
matching quality without rebuilding the system.

Matching policy:
- confidence >= 85 -> auto-merge
- 70 <= confidence < 85 -> manual review bucket (kept separate but reported)
- confidence < 70 -> keep separate

Implementation notes:
- We do NOT rely on exact string equality.
- We normalize punctuation/casing/ignored words.
- We expand a small set of common abbreviations (extend as needed).
- We compute a similarity score using a blend of token overlap and fuzzy
  similarity (difflib SequenceMatcher).
- Supports Arabic+English normalization heuristically (diacritics removal,
  common letter normalization).
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable


# -----------------------------
# Normalization helpers
# -----------------------------

_IGNORED_PREFIXES = [
    "introduction to",
    "introduction",
    "fundamentals",
    "basics",
]

# Arabic variants often appear; include conservative patterns.
_IGNORED_AR_PREFIXES = [
    "مقدمة الى",
    "مقدمة ل",
    "مدخل الى",
    "أساسيات",
    "الأساسيات",
    "مبادئ",
]

# Very common abbreviations in engineering/CS curricula.
_ABBREVIATIONS = {
    "dsp": "digital signal processing",
}


def _strip_diacritics_ar(s: str) -> str:
    # remove Arabic diacritics using unicode categories
    out = []
    for ch in s:
        if unicodedata.category(ch) == "Mn":
            continue
        out.append(ch)
    return "".join(out)


def _normalize_ar_letters(s: str) -> str:
    # normalize a small set of Arabic letter variants
    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ى": "ي",
        "ة": "ه",
        "ؤ": "و",
        "ئ": "ي",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s


def _remove_punctuation(s: str) -> str:
    # keep alphanumerics + whitespace; treat Arabic letters as alphanumerics via regex class
    # remove all punctuation/symbols except whitespace
    s = re.sub(r"[\-_/\\()\[\]{}.,;:!?\"'`~@#$%^&*+=<>|]", " ", s)
    return s


def _tokenize(s: str) -> list[str]:
    return [t for t in re.split(r"\s+", s.strip()) if t]


def normalize_course_text(text: str) -> str:
    """Normalize course text for matching."""
    if text is None:
        return ""

    s = str(text)
    s = s.strip()
    if not s:
        return ""

    # unicode normalization
    s = unicodedata.normalize("NFKC", s)
    s = _strip_diacritics_ar(s)
    s = _normalize_ar_letters(s)

    # English casing
    s = s.lower()

    # punctuation -> spaces
    s = _remove_punctuation(s)

    # Expand abbreviations (word-based to avoid replacing inside longer tokens)
    tokens = _tokenize(s)
    expanded: list[str] = []
    for t in tokens:
        if t in _ABBREVIATIONS:
            expanded.extend(_tokenize(_ABBREVIATIONS[t]))
        else:
            expanded.append(t)
    s = " ".join(expanded)

    # Remove ignored prefixes/words (English + Arabic)
    # Apply prefix removal on beginning of string.
    for p in _IGNORED_PREFIXES:
        if s.startswith(p):
            s = s[len(p) :].strip()
            break
    for p in _IGNORED_AR_PREFIXES:
        if s.startswith(p):
            s = s[len(p) :].strip()
            break

    # Plural/singular heuristic (English only): remove trailing 's' for tokens > 3 chars.
    # This is intentionally conservative.
    out_tokens: list[str] = []
    for t in _tokenize(s):
        if re.match(r"^[a-z]{4,}$", t) and t.endswith("s") and not t.endswith("ss"):
            out_tokens.append(t[:-1])
        else:
            out_tokens.append(t)

    return " ".join(out_tokens).strip()


# -----------------------------
# Similarity + scoring
# -----------------------------


def _token_overlap_similarity(a: str, b: str) -> float:
    ta = set(_tokenize(a))
    tb = set(_tokenize(b))
    if not ta or not tb:
        return 0.0
    inter = ta.intersection(tb)
    # Use Jaccard-like normalization
    union = ta.union(tb)
    return len(inter) / len(union) if union else 0.0


def _fuzzy_similarity(a: str, b: str) -> float:
    # difflib works on normalized strings.
    return difflib.SequenceMatcher(a=a, b=b).ratio() if (a or b) else 0.0


def _acronym_boost(original_a: str, original_b: str, norm_a: str, norm_b: str) -> float:
    # If one contains an abbreviation token and the other contains its expanded form,
    # the normalization already helps; still, small boost if abbreviations were present.
    orig = (original_a or "") + " " + (original_b or "")
    score = 0.0
    for abbr, expanded in _ABBREVIATIONS.items():
        if re.search(rf"\b{re.escape(abbr)}\b", orig.lower()):
            # boost when normalized strings contain expanded words
            if all(tok in norm_a for tok in _tokenize(expanded)) or all(tok in norm_b for tok in _tokenize(expanded)):
                score = max(score, 0.05)
    return score


def compute_match_confidence(a_text: str, b_text: str) -> float:
    """Return confidence in [0..100]."""
    a_norm = normalize_course_text(a_text)
    b_norm = normalize_course_text(b_text)
    if not a_norm or not b_norm:
        return 0.0

    overlap = _token_overlap_similarity(a_norm, b_norm)  # 0..1
    fuzzy = _fuzzy_similarity(a_norm, b_norm)  # 0..1

    # blend: overlap tends to be more robust for curriculum names; fuzzy helps
    # for ordering/formatting differences.
    blend = 0.55 * overlap + 0.45 * fuzzy

    # Minor acronym boost
    blend += _acronym_boost(a_text, b_text, a_norm, b_norm)

    # clamp
    blend = min(1.0, max(0.0, blend))
    return round(blend * 100, 2)


@dataclass(frozen=True)
class CourseMatchDecision:
    confidence: float
    status: str  # 'auto_merge' | 'manual_review' | 'keep_separate'


def decide_match(confidence: float) -> CourseMatchDecision:
    if confidence >= 85:
        return CourseMatchDecision(confidence=confidence, status="auto_merge")
    if confidence >= 70:
        return CourseMatchDecision(confidence=confidence, status="manual_review")
    return CourseMatchDecision(confidence=confidence, status="keep_separate")


# -----------------------------
# Convenience: grouping by similarity
# -----------------------------


def find_equivalent_courses(
    course_texts: Iterable[str],
    *,
    max_candidates: int = 50,
) -> list[list[str]]:
    """Cluster course strings using greedy similarity.

    This is used only for small sets (per sheet) to keep complexity bounded.
    Returns list of clusters; each cluster is a list of original strings.
    """
    texts = [t for t in course_texts if t]
    # cap for safety
    texts = texts[:max_candidates]
    if not texts:
        return []

    clusters: list[list[str]] = []
    used: set[str] = set()

    for i, t in enumerate(texts):
        if t in used:
            continue
        used.add(t)
        cluster = [t]
        # compare to others not used
        for j in range(i + 1, len(texts)):
            t2 = texts[j]
            if t2 in used:
                continue
            conf = compute_match_confidence(t, t2)
            dec = decide_match(conf)
            if dec.status == "auto_merge":
                used.add(t2)
                cluster.append(t2)
        clusters.append(cluster)

    return clusters

