"""Tests for app.ml.training.train -- the offline training pipeline."""

from __future__ import annotations

import pytest

from app.ml.dataset import DEFAULT_DATASET_PATH
from app.ml.training.train import TrainingResult, train


class TestTrainingPipeline:
    def test_train_produces_result(self, tmp_path):
        artifact_path = tmp_path / "test_intent_classifier.joblib"
        result = train(
            dataset_path=DEFAULT_DATASET_PATH, artifact_path=artifact_path
        )
        assert isinstance(result, TrainingResult)

    def test_train_writes_artifact_file(self, tmp_path):
        artifact_path = tmp_path / "test_intent_classifier.joblib"
        train(dataset_path=DEFAULT_DATASET_PATH, artifact_path=artifact_path)
        assert artifact_path.exists()
        assert artifact_path.stat().st_size > 0

    def test_train_reports_reasonable_accuracy(self, tmp_path):
        artifact_path = tmp_path / "test_intent_classifier.joblib"
        result = train(
            dataset_path=DEFAULT_DATASET_PATH, artifact_path=artifact_path
        )
        # A lightweight TF-IDF + Logistic Regression model on a small,
        # deliberately compact dataset won't be perfect; just assert it
        # is clearly better than random guessing among 4 classes (0.25).
        assert result.accuracy > 0.25

    def test_train_split_sizes_sum_to_dataset_size(self, tmp_path):
        from app.ml.dataset import load_dataset

        artifact_path = tmp_path / "test_intent_classifier.joblib"
        result = train(
            dataset_path=DEFAULT_DATASET_PATH, artifact_path=artifact_path
        )
        total = len(load_dataset(DEFAULT_DATASET_PATH))
        assert result.train_size + result.test_size == total

    def test_train_raises_on_too_small_class(self, tmp_path):
        dataset_file = tmp_path / "tiny.csv"
        dataset_file.write_text(
            "text,intent\n"
            "Where is it?,NAVIGATION\n"
            "How do I get there?,NAVIGATION\n"
            "Help,HELP\n",  # only 1 HELP example -- too small to split
            encoding="utf-8",
        )
        artifact_path = tmp_path / "unused.joblib"
        with pytest.raises(ValueError):
            train(dataset_path=dataset_file, artifact_path=artifact_path)

    def test_training_is_deterministic(self, tmp_path):
        artifact_a = tmp_path / "a.joblib"
        artifact_b = tmp_path / "b.joblib"
        result_a = train(dataset_path=DEFAULT_DATASET_PATH, artifact_path=artifact_a)
        result_b = train(dataset_path=DEFAULT_DATASET_PATH, artifact_path=artifact_b)
        assert result_a.accuracy == result_b.accuracy
        assert result_a.train_size == result_b.train_size
