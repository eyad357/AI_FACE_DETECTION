"""
Tests for app.ml.intent_bridge.

Deliberately does NOT import app.speech anywhere in this file. The
whole point of translate_intent() is that it works against ANY
structurally-compatible target Enum supplied by the caller, without
app.ml ever importing app.speech. A local dummy Enum (mirroring
Speech's real member names) is used here to prove that genericity
directly, rather than accidentally re-introducing the very ML->Speech
import this module exists to avoid.
"""

from __future__ import annotations

from enum import Enum

import pytest

from app.ml.intent_bridge import IntentTranslationError, translate_intent
from app.models.schemas import IntentResult
from app.models.schemas import IntentType as MLIntentType


class _DummySpeechLikeIntentType(Enum):
    """
    Mirrors app.speech.intent.IntentType's member names exactly,
    without importing app.speech. Standing in for "some other module's
    Enum" to prove translate_intent() is generic, not Speech-specific.
    """

    INFORMATION = "INFORMATION"
    NAVIGATION = "NAVIGATION"
    COMBINED = "COMBINED"
    HELP = "HELP"
    UNKNOWN = "UNKNOWN"


class _DummyIncompleteEnum(Enum):
    """Deliberately missing a member, to exercise the failure path."""

    INFORMATION = "INFORMATION"
    UNKNOWN = "UNKNOWN"


def _result(intent: MLIntentType) -> IntentResult:
    return IntentResult(intent=intent, confidence=0.9, raw_text="test")


class TestTranslateIntentSuccess:
    @pytest.mark.parametrize(
        "intent",
        [
            MLIntentType.INFORMATION,
            MLIntentType.NAVIGATION,
            MLIntentType.COMBINED,
            MLIntentType.HELP,
            MLIntentType.UNKNOWN,
        ],
    )
    def test_translates_every_member_by_name(self, intent: MLIntentType) -> None:
        result = _result(intent)
        translated = translate_intent(result, _DummySpeechLikeIntentType)
        assert isinstance(translated, _DummySpeechLikeIntentType)
        assert translated.name == intent.name

    def test_does_not_require_matching_class(self) -> None:
        # Confirms the two enums are genuinely distinct classes, and
        # translation still works purely by member name.
        result = _result(MLIntentType.NAVIGATION)
        translated = translate_intent(result, _DummySpeechLikeIntentType)
        assert translated is not result.intent
        assert translated.__class__ is not result.intent.__class__


class TestTranslateIntentFailureModes:
    def test_raises_type_error_for_non_intent_result(self) -> None:
        with pytest.raises(TypeError):
            translate_intent("not an IntentResult", _DummySpeechLikeIntentType)  # type: ignore[arg-type]

    def test_raises_translation_error_for_missing_member(self) -> None:
        result = _result(MLIntentType.NAVIGATION)
        with pytest.raises(IntentTranslationError):
            translate_intent(result, _DummyIncompleteEnum)


class TestModuleIsolation:
    def test_module_does_not_import_app_speech(self) -> None:
        """
        Static guarantee that app.ml.intent_bridge never imports
        app.speech, mirroring the AST-based isolation checks used
        elsewhere in this project (e.g. tests/dl/test_dependency_isolation.py).
        """
        import ast
        import inspect

        import app.ml.intent_bridge as bridge_module

        source = inspect.getsource(bridge_module)
        tree = ast.parse(source)

        forbidden_roots = {"app.speech", "app.ui", "app.integration", "app.robot"}
        found = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    found.add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                found.add(node.module)

        for forbidden in forbidden_roots:
            assert not any(
                mod == forbidden or mod.startswith(forbidden + ".")
                for mod in found
            ), f"app.ml.intent_bridge must not import {forbidden}"
