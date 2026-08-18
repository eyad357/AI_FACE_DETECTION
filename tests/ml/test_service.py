"""Tests for app.ml.service -- the public ML intent classification API."""

from __future__ import annotations

import pytest

from app.ml.inference.inference import ArtifactNotFoundError
from app.ml.service import MLIntentService
from app.models.schemas import IntentResult, IntentType


@pytest.fixture(scope="module")
def service() -> MLIntentService:
    return MLIntentService()


class TestIntentClassification:
    """
    These use questions the trained model classifies correctly (verified
    against the committed artifact) so results are deterministic.
    """

    def test_navigation_classification(self, service):
        result = service.predict("Where is the AI Lab?")
        assert result.intent == IntentType.NAVIGATION

    def test_information_classification(self, service):
        result = service.predict("Tell me about the robotics program")
        assert result.intent == IntentType.INFORMATION

    def test_combined_classification(self, service):
        result = service.predict(
            "Where is the library and what services does it offer?"
        )
        assert result.intent == IntentType.COMBINED

    def test_help_classification(self, service):
        result = service.predict("I need help")
        assert result.intent == IntentType.HELP


class TestInputHandling:
    def test_empty_string_returns_unknown(self, service):
        result = service.predict("")
        assert result.intent == IntentType.UNKNOWN
        assert result.confidence == 0.0

    def test_whitespace_only_returns_unknown(self, service):
        result = service.predict("   \n\t  ")
        assert result.intent == IntentType.UNKNOWN
        assert result.confidence == 0.0

    def test_non_string_input_returns_unknown(self, service):
        result = service.predict(None)  # type: ignore[arg-type]
        assert result.intent == IntentType.UNKNOWN
        assert result.confidence == 0.0

    def test_numeric_input_returns_unknown(self, service):
        result = service.predict(12345)  # type: ignore[arg-type]
        assert result.intent == IntentType.UNKNOWN


class TestConfidenceRange:
    @pytest.mark.parametrize(
        "text",
        [
            "Where is the AI Lab?",
            "Tell me about the robotics program",
            "I need help",
            "What is the capital of the moon and where is it",
        ],
    )
    def test_confidence_within_bounds(self, service, text):
        result = service.predict(text)
        assert 0.0 <= result.confidence <= 1.0


class TestResultContract:
    def test_result_is_intent_result(self, service):
        result = service.predict("Where is the AI Lab?")
        assert isinstance(result, IntentResult)

    def test_result_preserves_raw_text(self, service):
        text = "Where is the AI Lab?"
        result = service.predict(text)
        assert result.raw_text == text

    def test_intent_result_rejects_bad_intent_type(self):
        with pytest.raises(ValueError):
            IntentResult(intent="NAVIGATION", confidence=0.5, raw_text="x")

    def test_intent_result_rejects_out_of_range_confidence(self):
        with pytest.raises(ValueError):
            IntentResult(
                intent=IntentType.NAVIGATION, confidence=1.5, raw_text="x"
            )
        with pytest.raises(ValueError):
            IntentResult(
                intent=IntentType.NAVIGATION, confidence=-0.1, raw_text="x"
            )

    def test_intent_result_rejects_non_string_raw_text(self):
        with pytest.raises(ValueError):
            IntentResult(intent=IntentType.NAVIGATION, confidence=0.5, raw_text=123)

    def test_intent_result_is_frozen(self):
        result = IntentResult(
            intent=IntentType.HELP, confidence=0.9, raw_text="I need help"
        )
        with pytest.raises(Exception):
            result.confidence = 0.1  # type: ignore[misc]


class TestMissingArtifactBehavior:
    def test_missing_artifact_raises_clear_error(self, tmp_path):
        service = MLIntentService(artifact_path=tmp_path / "missing.joblib")
        with pytest.raises(ArtifactNotFoundError):
            service.predict("Where is the AI Lab?")

    def test_missing_artifact_does_not_affect_empty_input(self, tmp_path):
        # Empty input short-circuits before touching the artifact at all.
        service = MLIntentService(artifact_path=tmp_path / "missing.joblib")
        result = service.predict("")
        assert result.intent == IntentType.UNKNOWN
