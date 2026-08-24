"""Tests for app.ml.dataset -- dataset loading and validation."""

from __future__ import annotations

import pytest

from app.ml.dataset import (
    DatasetValidationError,
    DEFAULT_DATASET_PATH,
    dataset_class_counts,
    load_dataset,
)
from app.models.schemas import IntentType


class TestLoadDefaultDataset:
    def test_default_dataset_loads(self):
        examples = load_dataset()
        assert len(examples) > 0

    def test_default_dataset_path_exists(self):
        assert DEFAULT_DATASET_PATH.exists()

    def test_all_intents_represented(self):
        examples = load_dataset()
        labels = {e.intent for e in examples}
        expected = {
            name
            for name in IntentType.__members__
            if name != IntentType.UNKNOWN.name
        }
        assert labels == expected

    def test_dataset_reasonably_balanced(self):
        examples = load_dataset()
        counts = dataset_class_counts(examples)
        # No class should be wildly out of proportion to the others.
        assert max(counts.values()) <= 3 * min(counts.values())

    def test_each_class_has_at_least_two_examples(self):
        examples = load_dataset()
        counts = dataset_class_counts(examples)
        assert all(count >= 2 for count in counts.values())


class TestDatasetValidation:
    def test_missing_file_raises(self, tmp_path):
        missing_path = tmp_path / "does_not_exist.csv"
        with pytest.raises(DatasetValidationError):
            load_dataset(missing_path)

    def test_wrong_header_raises(self, tmp_path):
        bad_file = tmp_path / "bad_header.csv"
        bad_file.write_text("question,label\nHello,HELP\n", encoding="utf-8")
        with pytest.raises(DatasetValidationError):
            load_dataset(bad_file)

    def test_empty_text_raises(self, tmp_path):
        bad_file = tmp_path / "empty_text.csv"
        bad_file.write_text("text,intent\n,HELP\n", encoding="utf-8")
        with pytest.raises(DatasetValidationError):
            load_dataset(bad_file)

    def test_unknown_intent_label_raises(self, tmp_path):
        bad_file = tmp_path / "unknown_label.csv"
        bad_file.write_text(
            "text,intent\nWhere is it?,NOT_A_REAL_INTENT\n", encoding="utf-8"
        )
        with pytest.raises(DatasetValidationError):
            load_dataset(bad_file)

    def test_unknown_is_not_a_valid_training_label(self, tmp_path):
        # UNKNOWN is a runtime fallback only, never a training label.
        bad_file = tmp_path / "unknown_as_label.csv"
        bad_file.write_text(
            "text,intent\nSomething weird,UNKNOWN\n", encoding="utf-8"
        )
        with pytest.raises(DatasetValidationError):
            load_dataset(bad_file)

    def test_empty_file_raises(self, tmp_path):
        bad_file = tmp_path / "header_only.csv"
        bad_file.write_text("text,intent\n", encoding="utf-8")
        with pytest.raises(DatasetValidationError):
            load_dataset(bad_file)

    def test_valid_minimal_dataset_loads(self, tmp_path):
        good_file = tmp_path / "minimal.csv"
        good_file.write_text(
            "text,intent\nWhere is the lab?,NAVIGATION\nHelp me,HELP\n",
            encoding="utf-8",
        )
        examples = load_dataset(good_file)
        assert len(examples) == 2
        assert examples[0].intent == "NAVIGATION"
