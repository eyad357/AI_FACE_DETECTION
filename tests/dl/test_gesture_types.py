"""
Tests for the DL gesture contract (app.dl.models.gesture_types).

Require no GPU, camera, robot hardware, internet, or external services.
"""

from datetime import datetime, timezone

import pytest

from app.dl.models.gesture_types import DLError, GestureLabel, GestureResult


class TestGestureVocabulary:
    """Pins down the DL gesture vocabulary so it cannot silently drift."""

    def test_expected_labels_exist(self):
        expected = {"WAVE", "STOP", "POINT", "UNKNOWN"}
        actual = {member.value for member in GestureLabel}
        assert actual == expected

    def test_label_values_match_names(self):
        for member in GestureLabel:
            assert member.value == member.name


class TestGestureResultValidation:
    def _scores(self, wave=0.7, stop=0.1, point=0.1, unknown=0.1):
        return {
            "WAVE": wave,
            "STOP": stop,
            "POINT": point,
            "UNKNOWN": unknown,
        }

    def test_valid_result_constructs(self):
        result = GestureResult(
            gesture=GestureLabel.WAVE,
            confidence=0.7,
            scores=self._scores(),
            timestamp=datetime.now(timezone.utc),
        )
        assert result.gesture is GestureLabel.WAVE
        assert result.confidence == 0.7
        assert result.metadata == {}

    def test_rejects_non_gesture_label(self):
        with pytest.raises(ValueError):
            GestureResult(
                gesture="WAVE",  # not a GestureLabel instance
                confidence=0.7,
                scores=self._scores(),
                timestamp=datetime.now(timezone.utc),
            )

    @pytest.mark.parametrize("confidence", [-0.01, 1.01, -5.0, 2.0])
    def test_rejects_out_of_range_confidence(self, confidence):
        with pytest.raises(ValueError):
            GestureResult(
                gesture=GestureLabel.WAVE,
                confidence=confidence,
                scores=self._scores(),
                timestamp=datetime.now(timezone.utc),
            )

    def test_rejects_score_keys_not_matching_vocabulary(self):
        with pytest.raises(ValueError):
            GestureResult(
                gesture=GestureLabel.WAVE,
                confidence=0.7,
                scores={"WAVE": 0.7, "SOMETHING_ELSE": 0.3},
                timestamp=datetime.now(timezone.utc),
            )

    def test_rejects_scores_not_summing_to_one(self):
        with pytest.raises(ValueError):
            GestureResult(
                gesture=GestureLabel.WAVE,
                confidence=0.7,
                scores={"WAVE": 0.7, "STOP": 0.7, "POINT": 0.0, "UNKNOWN": 0.0},
                timestamp=datetime.now(timezone.utc),
            )

    def test_empty_scores_dict_is_allowed(self):
        # unknown() with no distribution available at all.
        result = GestureResult(
            gesture=GestureLabel.UNKNOWN,
            confidence=0.0,
            scores={},
            timestamp=datetime.now(timezone.utc),
        )
        assert result.scores == {}

    def test_is_frozen(self):
        result = GestureResult(
            gesture=GestureLabel.WAVE,
            confidence=0.7,
            scores=self._scores(),
            timestamp=datetime.now(timezone.utc),
        )
        with pytest.raises(Exception):
            result.confidence = 0.9  # type: ignore[misc]


class TestGestureResultUnknownConstructor:
    def test_unknown_defaults(self):
        result = GestureResult.unknown(reason="low_confidence")
        assert result.gesture is GestureLabel.UNKNOWN
        assert result.confidence == 0.0
        assert result.scores == {}
        assert result.metadata == {"reason": "low_confidence"}

    def test_unknown_with_scores_and_confidence(self):
        scores = {"WAVE": 0.3, "STOP": 0.3, "POINT": 0.3, "UNKNOWN": 0.1}
        result = GestureResult.unknown(
            reason="low_confidence", scores=scores, confidence=0.3
        )
        assert result.confidence == 0.3
        assert result.scores == scores
        assert result.metadata["reason"] == "low_confidence"


class TestDLError:
    def test_dlerror_is_runtime_error(self):
        assert issubclass(DLError, RuntimeError)

    def test_dlerror_can_be_raised_and_caught(self):
        with pytest.raises(DLError):
            raise DLError("something went wrong")
