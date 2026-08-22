"""
Tests for app.speech.language (Language / detect_language / PHRASES /
phrase()).
"""

import pytest

from app.speech.language import PHRASES, Language, PhraseKey, detect_language, phrase


class TestLanguageDetection:
    def test_english_text_detected_as_english(self):
        assert detect_language("Where is the AI Lab?") is Language.ENGLISH

    def test_arabic_text_detected_as_arabic(self):
        assert detect_language("أين المختبر؟") is Language.ARABIC

    def test_empty_text_falls_back_to_default(self):
        assert detect_language("") is Language.default()

    def test_none_does_not_raise(self):
        assert detect_language(None) is Language.default()  # type: ignore[arg-type]

    def test_mixed_text_with_any_arabic_char_detected_as_arabic(self):
        assert detect_language("hello مرحبا") is Language.ARABIC


class TestPhraseTable:
    def test_every_key_has_every_language(self):
        for key in PhraseKey:
            for language in Language:
                assert language in PHRASES[key], f"{key} missing {language}"
                assert PHRASES[key][language]

    def test_phrase_lookup_english(self):
        text = phrase(PhraseKey.GREETING, Language.ENGLISH)
        assert text

    def test_phrase_lookup_arabic(self):
        text = phrase(PhraseKey.GREETING, Language.ARABIC)
        assert text

    def test_phrase_formatting_with_destination(self):
        text = phrase(PhraseKey.NAVIGATION_CONFIRMATION, Language.ENGLISH, destination="the Library")
        assert "the Library" in text

    def test_phrase_missing_format_arg_does_not_raise(self):
        # NAVIGATION_CONFIRMATION expects `destination`; omitting it
        # must not crash a conversation turn.
        text = phrase(PhraseKey.NAVIGATION_CONFIRMATION, Language.ENGLISH)
        assert isinstance(text, str)
