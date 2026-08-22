"""
Language support for the Speech & Conversation layer.

Responsibility: represent which language a conversation is in, provide
a lightweight (non-ML, offline) heuristic to guess a language from raw
text, and expose small phrase-template tables so response composition
(app.speech.response) never hardcodes English strings inline.

This module intentionally does NOT implement full translation
infrastructure (no external translation API, no third-party i18n
library, no network access) — none exists elsewhere in the repository
for it to reuse, and the phase instructions explicitly say not to
require one. Instead it defines clean extension points:

    - Language: the closed set of supported languages.
    - detect_language(text): a deterministic, offline guess.
    - PHRASES: a Dict[PhraseKey, Dict[Language, str]] template table.
    - phrase(key, language, **kwargs): safe template lookup/formatting.

Adding a new language later means adding one more Language member and
filling in its row in PHRASES — no other module needs to change.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict


class Language(Enum):
    """Supported conversation languages."""

    ENGLISH = "en"
    ARABIC = "ar"

    @classmethod
    def default(cls) -> "Language":
        return cls.ENGLISH


# Unicode range for Arabic script (covers standard Arabic letters).
# A simple, deterministic, offline heuristic: if any character in the
# input falls in this range, treat the utterance as Arabic. This is
# intentionally simple (no language-detection library / network call)
# and sufficient for a capstone-level, Arabic-ready design.
_ARABIC_RANGE = (0x0600, 0x06FF)


def detect_language(text: str) -> Language:
    """
    Guess the language of `text` using a deterministic, offline
    heuristic (Arabic-script character presence). Never raises; falls
    back to Language.default() for empty/non-string/ambiguous input.
    """
    if not isinstance(text, str) or not text.strip():
        return Language.default()

    for ch in text:
        codepoint = ord(ch)
        if _ARABIC_RANGE[0] <= codepoint <= _ARABIC_RANGE[1]:
            return Language.ARABIC

    return Language.default()


class PhraseKey(Enum):
    """Keys for the language-aware phrase template table."""

    GREETING = "GREETING"
    HELP = "HELP"
    INFORMATION_UNKNOWN_TOPIC = "INFORMATION_UNKNOWN_TOPIC"
    NAVIGATION_CONFIRMATION = "NAVIGATION_CONFIRMATION"
    NAVIGATION_CLARIFICATION = "NAVIGATION_CLARIFICATION"
    INFORMATION_CLARIFICATION = "INFORMATION_CLARIFICATION"
    CONFIRMATION_ACK_YES = "CONFIRMATION_ACK_YES"
    CONFIRMATION_ACK_NO = "CONFIRMATION_ACK_NO"
    FALLBACK_UNKNOWN = "FALLBACK_UNKNOWN"
    MALFORMED_INPUT = "MALFORMED_INPUT"
    CONTEXT_RESET = "CONTEXT_RESET"


# Every key MUST have an entry for every Language member — verified by
# tests/speech/test_language.py, so a missing translation is caught
# immediately rather than silently falling back to English at runtime.
PHRASES: Dict[PhraseKey, Dict[Language, str]] = {
    PhraseKey.GREETING: {
        Language.ENGLISH: "Hello! I'm the lab guide assistant. How can I help you today?",
        Language.ARABIC: "مرحباً! أنا مساعد دليل المختبر. كيف يمكنني مساعدتك اليوم؟",
    },
    PhraseKey.HELP: {
        Language.ENGLISH: (
            "You can ask me where something is, ask me to guide you "
            "somewhere, or ask about the lab, robotics, or training."
        ),
        Language.ARABIC: (
            "يمكنك أن تسألني عن مكان شيء ما، أو تطلب مني إرشادك إلى "
            "مكان ما، أو تسأل عن المختبر أو الروبوتات أو التدريب."
        ),
    },
    PhraseKey.INFORMATION_UNKNOWN_TOPIC: {
        Language.ENGLISH: "I don't have information about that yet. Could you tell me more specifically what you're looking for?",
        Language.ARABIC: "ليس لدي معلومات عن ذلك حتى الآن. هل يمكنك توضيح ما تبحث عنه بالتحديد؟",
    },
    PhraseKey.NAVIGATION_CONFIRMATION: {
        Language.ENGLISH: "Sure. I'll guide you to {destination}.",
        Language.ARABIC: "بالتأكيد. سأقوم بإرشادك إلى {destination}.",
    },
    PhraseKey.NAVIGATION_CLARIFICATION: {
        Language.ENGLISH: "Where would you like me to guide you?",
        Language.ARABIC: "إلى أين تريد أن أرشدك؟",
    },
    PhraseKey.INFORMATION_CLARIFICATION: {
        Language.ENGLISH: "What would you like to know more about?",
        Language.ARABIC: "ما الذي تود معرفة المزيد عنه؟",
    },
    PhraseKey.CONFIRMATION_ACK_YES: {
        Language.ENGLISH: "Great, let's continue.",
        Language.ARABIC: "رائع، لنكمل.",
    },
    PhraseKey.CONFIRMATION_ACK_NO: {
        Language.ENGLISH: "No problem, let me know if you need anything else.",
        Language.ARABIC: "لا مشكلة، أخبرني إذا احتجت أي شيء آخر.",
    },
    PhraseKey.FALLBACK_UNKNOWN: {
        Language.ENGLISH: "Sorry, I didn't understand that. Could you rephrase it?",
        Language.ARABIC: "عذراً، لم أفهم ذلك. هل يمكنك إعادة الصياغة؟",
    },
    PhraseKey.MALFORMED_INPUT: {
        Language.ENGLISH: "I didn't catch that. Could you say it again?",
        Language.ARABIC: "لم أسمع ذلك بوضوح. هل يمكنك التكرار؟",
    },
    PhraseKey.CONTEXT_RESET: {
        Language.ENGLISH: "Okay, let's start over. How can I help you?",
        Language.ARABIC: "حسناً، لنبدأ من جديد. كيف يمكنني مساعدتك؟",
    },
}


def phrase(key: PhraseKey, language: Language, **kwargs: str) -> str:
    """
    Look up and format a phrase template.

    Falls back to Language.default() if `language` has no entry for
    `key` (should not happen given PHRASES covers every Language for
    every key, but handled defensively rather than raising KeyError
    for what would otherwise be a hard crash mid-conversation).
    """
    table = PHRASES.get(key, {})
    template = table.get(language) or table.get(Language.default(), "")
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        # A missing format argument must never crash a conversation
        # turn — fall back to the unformatted template.
        return template
