"""Simple language detection utilities for the mock provider and general use."""

from __future__ import annotations

import logging

logger = logging.getLogger("officepilot.language_utils")

# Language-specific keyword signatures for lightweight detection.
# Each language has a set of unique stopword/cue words that are unlikely to
# appear in other languages. Order matters — checked top to bottom.
_LANGUAGE_SIGNATURES: list[tuple[str, set[str]]] = [
    ("german", {"und", "die", "das", "der", "ist", "ein", "eine", "für", "auf",
                "mit", "zusammenfassung", "bericht", "herunterladen", "datei",
                "erstellen", "bitte", "sie", "ich", "nicht", "auch", "diesen"}),
    ("french", {"le", "la", "les", "des", "est", "dans", "pour", "avec",
                "téléchargement", "telechargement", "fichier", "tableur",
                "résumé", "resume", "sommaire", "rapport", "créer", "creer",
                "je", "tu", "nous", "vous", "pas", "sur", "une"}),
    ("spanish", {"el", "la", "los", "las", "es", "en", "un", "una",
                 "descarga", "descargas", "descargar", "archivo",
                 "resumen", "informe", "reporte", "crear", "para",
                 "con", "por", "del", "como", "más", "pero", "este"}),
    ("urdu_roman", {"hai", "hy", "hain", "ko", "ki", "ka", "ke", "kay",
                    "mein", "se", "sy", "karo", "karna", "kar",
                    "mujhe", "muje", "batao", "samri", "aaj", "aj",
                    "kal", "wala", "wali", "wale", "aur", "nahi"}),
]

# Fallback: if none of the above match strongly, check individual tokens
# for language-identifying characters.
_LATIN_ONLY = set("abcdefghijklmnopqrstuvwxyz")


def detect_language_simple(text: str) -> str:
    """Detect language using lightweight keyword heuristics.

    Returns one of: 'german', 'french', 'spanish', 'urdu_roman', 'en',
    or 'unknown'.
    """
    lower = text.lower().strip()
    if not lower:
        return "unknown"

    tokens = lower.split()
    if not tokens:
        return "unknown"

    scores: dict[str, int] = {}
    for lang, sig in _LANGUAGE_SIGNATURES:
        scores[lang] = sum(1 for t in tokens if t in sig)

    best_lang = max(scores, key=scores.get)  # type: ignore[arg-type]
    best_score = scores[best_lang]

    # Require at least 2 cue words for a non-English match
    if best_score >= 2 and best_lang != "urdu_roman":
        logger.debug("detect_language_simple: '%s' -> %s (score=%d)", text[:60], best_lang, best_score)
        return best_lang

    # Roman Urdu needs higher threshold because short tokens (ki, ka, ko)
    # can overlap with other languages
    if best_lang == "urdu_roman" and best_score >= 3:
        logger.debug("detect_language_simple: '%s' -> urdu_roman (score=%d)", text[:60], best_score)
        return "urdu_roman"

    # Default to English if Latin-only and no strong match
    logger.debug("detect_language_simple: '%s' -> en (fallback)", text[:60])
    return "en"
