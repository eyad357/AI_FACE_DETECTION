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


class TestLowConfidenceUnknownPolicy:
    """
    Verifies the documented confidence-threshold policy (see docs/ml.md,
    "Confidence threshold policy"): CONFIG.ml.min_confidence defaults to
    0.30, derived from the committed artifact's behavior on text with no
    training-vocabulary overlap (which bottoms out at ~0.294 confidence,
    the model's class-prior floor for this 4-class problem).
    """

    @pytest.mark.parametrize(
        "text",
        [
            "asdkfj qwoeiru zxcvvb",  # no vocabulary overlap at all
            "banana banana banana",
            "1234567890",
        ],
    )
    def test_no_vocabulary_overlap_returns_unknown(self, service, text):
        result = service.predict(text)
        assert result.intent == IntentType.UNKNOWN
        # Confidence is still reported (not zeroed) -- only the intent
        # is downgraded, per the documented policy.
        assert 0.0 <= result.confidence < 0.30

    def test_in_domain_predictions_clear_the_threshold(self, service):
        # Regression guard: the 0.30 floor must not be so high that it
        # swallows genuine in-domain predictions (see docs/ml.md for the
        # held-out-split evaluation this threshold was based on).
        result = service.predict("Where is the AI Lab?")
        assert result.intent != IntentType.UNKNOWN
        assert result.confidence >= 0.30

    def test_default_min_confidence_matches_documented_policy(self):
        from app.config import CONFIG

        assert CONFIG.ml.min_confidence == pytest.approx(0.30)


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
