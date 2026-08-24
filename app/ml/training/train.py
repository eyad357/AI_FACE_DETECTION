"""
Offline training pipeline for the ML intent classifier.

Responsibility: turn the labeled dataset (app.ml.dataset) into a
trained TF-IDF + Logistic Regression pipeline, evaluate it on a held-out
split, and persist the fitted pipeline to app.ml.artifacts so that
app.ml.inference can load it at runtime WITHOUT retraining.

This module is run explicitly, offline, e.g.:

    python -m app.ml.training.train

It must never be imported or executed automatically by application
runtime code (see app.ml.inference / app.ml.service).

Pipeline:

    dataset (app.ml.dataset)
        -> validation
        -> train/test split
        -> TF-IDF vectorization
        -> Logistic Regression
        -> evaluation
        -> saved artifact (joblib)
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from app.ml.dataset import DatasetExample, DEFAULT_DATASET_PATH, load_dataset
from app.ml.inference.inference import ARTIFACT_DIR, DEFAULT_ARTIFACT_PATH

# Kept small and fixed for reproducible offline training on a tiny
# dataset; not a runtime-tunable setting (see app.config.MLConfig for
# genuinely runtime-relevant ML settings).
_RANDOM_STATE = 42
_TEST_SIZE = 0.25


@dataclass(frozen=True)
class TrainingResult:
    """Summary of a single training run, returned for reporting/tests."""

    accuracy: float
    report: str
    train_size: int
    test_size: int
    artifact_path: Path


def _build_pipeline() -> Pipeline:
    """Construct an untrained TF-IDF + Logistic Regression pipeline."""
    return Pipeline(
        steps=[
            (
                "tfidf",
                TfidfVectorizer(
                    lowercase=True,
                    ngram_range=(1, 2),
                    min_df=1,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    max_iter=1000,
                    random_state=_RANDOM_STATE,
                ),
            ),
        ]
    )


def train(
    dataset_path: Path = DEFAULT_DATASET_PATH,
    artifact_path: Path = DEFAULT_ARTIFACT_PATH,
) -> TrainingResult:
    """
    Train the intent classifier and persist it to disk.

    Args:
        dataset_path: Path to the labeled "text,intent" CSV dataset.
        artifact_path: Where to save the fitted pipeline (joblib).

    Returns:
        A TrainingResult summarizing accuracy and split sizes.

    Raises:
        app.ml.dataset.DatasetValidationError: if the dataset is
            missing or malformed.
        ValueError: if the dataset is too small to stratify/split.
    """
    examples: List[DatasetExample] = load_dataset(dataset_path)

    texts = [e.text for e in examples]
    labels = [e.intent for e in examples]

    class_counts: dict = {}
    for label in labels:
        class_counts[label] = class_counts.get(label, 0) + 1
    if min(class_counts.values()) < 2:
        raise ValueError(
            "Each intent class needs at least 2 examples to allow a "
            f"train/test split; got counts={class_counts}"
        )

    x_train, x_test, y_train, y_test = train_test_split(
        texts,
        labels,
        test_size=_TEST_SIZE,
        random_state=_RANDOM_STATE,
        stratify=labels,
    )

    pipeline = _build_pipeline()
    pipeline.fit(x_train, y_train)

    y_pred = pipeline.predict(x_test)
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, zero_division=0)

    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    import joblib

    joblib.dump(pipeline, artifact_path)

    return TrainingResult(
        accuracy=float(accuracy),
        report=report,
        train_size=len(x_train),
        test_size=len(x_test),
        artifact_path=artifact_path,
    )


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="Train the TF-IDF + Logistic Regression intent classifier."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help="Path to the labeled text,intent CSV dataset.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_ARTIFACT_PATH,
        help="Where to save the trained artifact.",
    )
    args = parser.parse_args()

    result = train(dataset_path=args.dataset, artifact_path=args.out)

    print(f"Train examples: {result.train_size}")
    print(f"Test examples:  {result.test_size}")
    print(f"Accuracy:       {result.accuracy:.3f}")
    print()
    print(result.report)
    print(f"Artifact saved to: {result.artifact_path}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
