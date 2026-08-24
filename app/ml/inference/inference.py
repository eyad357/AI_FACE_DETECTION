"""
Runtime inference for the ML intent classifier.

Responsibility: load a previously trained artifact (produced offline by
app.ml.training.train) and use it to classify a single piece of text at
request time. This module never trains or retrains a model.

Consumed by app.ml.service, which exposes the public API. Callers
outside app.ml should not import this module directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

# Single source of truth for the default trained-artifact location.
# app.ml.training.train writes here; this module reads from here.
ARTIFACT_DIR = Path(__file__).resolve().parent.parent / "artifacts"
DEFAULT_ARTIFACT_PATH = ARTIFACT_DIR / "intent_classifier.joblib"

_PIPELINE_CACHE: dict = {}


class ArtifactNotFoundError(RuntimeError):
    """
    Raised when a trained model artifact cannot be found on disk.

    Runtime inference deliberately does NOT fall back to silently
    training a model -- if this is raised, run the offline training
    pipeline first (see docs/ml.md: "How to train").
    """


def load_pipeline(artifact_path: Path = DEFAULT_ARTIFACT_PATH):
    """
    Load a trained TF-IDF + Logistic Regression pipeline from disk.

    Results are cached in-process per artifact_path so repeated calls
    (e.g. many predictions in the same run) don't re-read the file.

    Args:
        artifact_path: Path to a joblib-serialized sklearn Pipeline
            produced by app.ml.training.train.

    Returns:
        The deserialized sklearn Pipeline.

    Raises:
        ArtifactNotFoundError: if no artifact exists at artifact_path.
    """
    cache_key = str(artifact_path)
    if cache_key in _PIPELINE_CACHE:
        return _PIPELINE_CACHE[cache_key]

    if not artifact_path.exists():
        raise ArtifactNotFoundError(
            f"No trained ML artifact found at {artifact_path}. "
            "Run the offline training pipeline first: "
            "`python -m app.ml.training.train` "
            "(see docs/ml.md)."
        )

    import joblib

    pipeline = joblib.load(artifact_path)
    _PIPELINE_CACHE[cache_key] = pipeline
    return pipeline


def predict_intent(
    text: str, artifact_path: Path = DEFAULT_ARTIFACT_PATH
) -> tuple[str, float]:
    """
    Classify a single piece of text using the trained pipeline.

    Args:
        text: Raw student question text (already validated as
            non-empty by the caller -- see app.ml.service).
        artifact_path: Path to the trained artifact to use.

    Returns:
        A (predicted_intent_label, confidence) tuple, where
        predicted_intent_label is an IntentType member name (str) and
        confidence is the model's predicted probability for that class,
        in [0.0, 1.0].

    Raises:
        ArtifactNotFoundError: if no trained artifact exists.
    """
    pipeline = load_pipeline(artifact_path)

    probabilities = pipeline.predict_proba([text])[0]
    classes = pipeline.classes_

    best_index = probabilities.argmax()
    predicted_label = str(classes[best_index])
    confidence = float(probabilities[best_index])

    return predicted_label, confidence


def clear_cache() -> None:
    """Clear the in-process pipeline cache. Primarily useful for tests."""
    _PIPELINE_CACHE.clear()
