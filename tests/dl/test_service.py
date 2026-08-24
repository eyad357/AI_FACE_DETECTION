"""
Tests for app.dl.service.GestureRecognitionService — the public DL API.

Require no GPU, camera, robot hardware, internet, or external services.
"""

import numpy as np
import pytest

from app.dl.config import DLConfig
from app.dl.dataset.fixture import _pattern_for_label
from app.dl.models.gesture_types import DLError, GestureLabel
from app.dl.models.network import GestureMLP
from app.dl.service import GestureRecognitionService


def _bgr_frame_for(label: GestureLabel, size):
    pattern = _pattern_for_label(label, size).astype(np.uint8)
    return np.stack([pattern, pattern, pattern], axis=-1)


class TestServiceConstruction:
    def test_default_construction_loads_shipped_trained_artifact(self):
        service = GestureRecognitionService()
        # The shipped artifact (built by
        # app.dl.training.train_fixture_model) should be present and
        # load successfully in this repository.
        assert service.model_source in ("trained_artifact", "untrained_fixture")

    def test_caller_provided_model_is_used_directly(self):
        model = GestureMLP.from_seed(input_dim=400, hidden_dim=24, num_classes=4, seed=0)
        service = GestureRecognitionService(model=model)
        assert service.model_source == "caller_provided"

    def test_require_trained_artifact_raises_when_missing(self, tmp_path):
        config = DLConfig(artifact_path=str(tmp_path / "does_not_exist.npz"))
        with pytest.raises(DLError):
            GestureRecognitionService(config=config, require_trained_artifact=True)

    def test_falls_back_to_untrained_fixture_when_artifact_missing(self, tmp_path):
        config = DLConfig(artifact_path=str(tmp_path / "does_not_exist.npz"))
        service = GestureRecognitionService(config=config, require_trained_artifact=False)
        assert service.model_source == "untrained_fixture"


class TestPredictContract:
    def test_predict_returns_gesture_result_for_valid_frame(self):
        service = GestureRecognitionService()
        frame = _bgr_frame_for(GestureLabel.WAVE, (20, 20))
        result = service.predict(frame)
        assert result.gesture in set(GestureLabel)
        assert 0.0 <= result.confidence <= 1.0

    def test_predict_raises_dlerror_for_invalid_input(self):
        service = GestureRecognitionService()
        with pytest.raises(DLError):
            service.predict(None)
        with pytest.raises(DLError):
            service.predict("not a frame")

    def test_predict_on_trained_model_recognizes_matching_pattern(self):
        service = GestureRecognitionService()
        if service.model_source != "trained_artifact":
            pytest.skip("No trained artifact available in this environment")
        for label in (GestureLabel.WAVE, GestureLabel.STOP, GestureLabel.POINT):
            frame = _bgr_frame_for(label, (20, 20))
            result = service.predict(frame)
            assert result.gesture is label, (
                f"expected {label} for its own clean synthetic pattern, "
                f"got {result.gesture} (scores={result.scores})"
            )

    def test_untrained_fixture_predictions_are_labeled(self, tmp_path):
        config = DLConfig(artifact_path=str(tmp_path / "does_not_exist.npz"))
        service = GestureRecognitionService(config=config)
        frame = np.zeros((20, 20, 3), dtype=np.uint8)
        result = service.predict(frame)
        assert result.metadata.get("model_source") == "untrained_fixture"

    def test_low_confidence_produces_unknown_with_reason(self):
        # A model whose weights are all zero produces a uniform
        # (maximally low-confidence, 0.25 each) softmax distribution,
        # which is guaranteed to be below any threshold > 0.25.
        model = GestureMLP(
            W1=np.zeros((400, 24), dtype=np.float32),
            b1=np.zeros(24, dtype=np.float32),
            W2=np.zeros((24, 4), dtype=np.float32),
            b2=np.zeros(4, dtype=np.float32),
        )
        config = DLConfig(confidence_threshold=0.5)
        service = GestureRecognitionService(model=model, config=config)
        frame = np.full((20, 20, 3), 128, dtype=np.uint8)
        result = service.predict(frame)
        assert result.gesture is GestureLabel.UNKNOWN
        assert result.metadata.get("reason") == "low_confidence"

    def test_scores_always_present_and_sum_to_one(self):
        service = GestureRecognitionService()
        frame = np.random.default_rng(0).integers(
            0, 255, size=(20, 20, 3), dtype=np.uint8
        )
        result = service.predict(frame)
        assert set(result.scores.keys()) == {"WAVE", "STOP", "POINT", "UNKNOWN"}
        assert abs(sum(result.scores.values()) - 1.0) < 1e-4


class TestModelInfo:
    def test_model_info_has_expected_keys(self):
        service = GestureRecognitionService()
        info = service.model_info
        for key in (
            "model_source",
            "input_dim",
            "hidden_dim",
            "num_classes",
            "num_params",
            "confidence_threshold",
        ):
            assert key in info

    def test_model_info_num_classes_matches_vocabulary(self):
        service = GestureRecognitionService()
        assert service.model_info["num_classes"] == len(set(GestureLabel))
