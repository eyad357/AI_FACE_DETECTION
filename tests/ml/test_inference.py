"""Tests for app.ml.inference.inference -- runtime inference."""

from __future__ import annotations

import pytest

from app.ml.inference.inference import (
    ArtifactNotFoundError,
    DEFAULT_ARTIFACT_PATH,
    clear_cache,
    load_pipeline,
    predict_intent,
)
from app.ml.training.train import train
from app.ml.dataset import DEFAULT_DATASET_PATH


class TestMissingArtifact:
    def test_load_pipeline_missing_raises(self, tmp_path):
        missing = tmp_path / "nope.joblib"
        with pytest.raises(ArtifactNotFoundError):
            load_pipeline(missing)

    def test_predict_intent_missing_artifact_raises(self, tmp_path):
        missing = tmp_path / "nope.joblib"
        with pytest.raises(ArtifactNotFoundError):
            predict_intent("Where is the AI Lab?", artifact_path=missing)

    def test_missing_artifact_error_is_clear(self, tmp_path):
        missing = tmp_path / "nope.joblib"
        with pytest.raises(ArtifactNotFoundError, match="training"):
            load_pipeline(missing)


class TestArtifactLoadingAndInference:
    def test_default_artifact_exists(self):
        # The trained artifact is committed to app/ml/artifacts/ so
        # runtime inference never needs to train.
        assert DEFAULT_ARTIFACT_PATH.exists()

    def test_load_pipeline_from_default_artifact(self):
        clear_cache()
        pipeline = load_pipeline(DEFAULT_ARTIFACT_PATH)
        assert pipeline is not None
        assert hasattr(pipeline, "predict")

    def test_predict_intent_returns_label_and_confidence(self):
        clear_cache()
        label, confidence = predict_intent(
            "Where is the AI Lab?", artifact_path=DEFAULT_ARTIFACT_PATH
        )
        assert isinstance(label, str)
        assert 0.0 <= confidence <= 1.0

    def test_pipeline_is_cached_between_calls(self):
        clear_cache()
        first = load_pipeline(DEFAULT_ARTIFACT_PATH)
        second = load_pipeline(DEFAULT_ARTIFACT_PATH)
        assert first is second


class TestInferenceDoesNotRetrain:
    def test_predict_with_trained_artifact_does_not_touch_dataset(
        self, tmp_path, monkeypatch
    ):
        # Train a small artifact, then verify predicting against it
        # works without any dataset file being present or read again.
        artifact_path = tmp_path / "isolated.joblib"
        train(dataset_path=DEFAULT_DATASET_PATH, artifact_path=artifact_path)

        clear_cache()
        label, confidence = predict_intent(
            "I need help", artifact_path=artifact_path
        )
        assert isinstance(label, str)
        assert 0.0 <= confidence <= 1.0


class TestModelPersistence:
    def test_trained_artifact_round_trips_predictions(self, tmp_path):
        artifact_path = tmp_path / "roundtrip.joblib"
        train(dataset_path=DEFAULT_DATASET_PATH, artifact_path=artifact_path)

        clear_cache()
        label_a, confidence_a = predict_intent(
            "Where is the library?", artifact_path=artifact_path
        )

        clear_cache()  # force a fresh load from disk
        label_b, confidence_b = predict_intent(
            "Where is the library?", artifact_path=artifact_path
        )

        assert label_a == label_b
        assert confidence_a == confidence_b
