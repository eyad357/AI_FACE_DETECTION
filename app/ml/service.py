"""
ML public API — intent classification service.

Responsibility: "Given a student's free-text question, what is their
intent?" Nothing more. This module does NOT decide what to do about the
intent (route to Guide, Navigation, both, or a help response) -- that
remains a future orchestration layer's job (app.main), mirroring how
app.decision owns state and app.guide owns content today.

Usage:

    from app.ml.service import MLIntentService

    service = MLIntentService()
    result = service.predict("Where is the AI Lab?")  # -> IntentResult

Callers do NOT need to know about TF-IDF, Logistic Regression, the
artifact file format, the vectorizer, or preprocessing -- all of that is
encapsulated in app.ml.inference.

Dependency rules (enforced, see docs/ml.md and app/ml/__init__.py):
    ML MUST NOT import app.vision, app.robot, app.decision, app.guide,
    app.navigation, app.dl, app.ui, or app.main.
    ML MAY use shared contracts from app.models.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.config import CONFIG
from app.ml.inference.inference import (
    ArtifactNotFoundError,
    DEFAULT_ARTIFACT_PATH,
    predict_intent,
)
from app.models.schemas import IntentResult, IntentType
from app.utils.logger import get_logger

logger = get_logger(__name__)

__all__ = ["MLIntentService", "ArtifactNotFoundError"]


class MLIntentService:
    """
    Public entry point for ML intent classification.

    A thin, stateless-from-the-caller's-perspective wrapper around
    app.ml.inference: it loads the trained artifact (once, lazily) and
    turns raw text into a validated IntentResult.
    """

    def __init__(self, artifact_path: Optional[Path] = None) -> None:
        """
        Args:
            artifact_path: Optional override for the trained artifact
                location. Defaults to app.config.CONFIG.ml.artifact_dir
                (if set) or the bundled app/ml/artifacts location.
        """
        if artifact_path is not None:
            self._artifact_path = artifact_path
        elif CONFIG.ml.artifact_dir:
            self._artifact_path = (
                Path(CONFIG.ml.artifact_dir) / DEFAULT_ARTIFACT_PATH.name
            )
        else:
            self._artifact_path = DEFAULT_ARTIFACT_PATH

    def predict(self, text: str) -> IntentResult:
        """
        Classify a student's free-text question into an intent.

        Args:
            text: The raw question text.

        Returns:
            An IntentResult with the predicted intent, confidence, and
            the original raw_text. If the input is empty/blank, or the
            model's confidence falls below
            CONFIG.ml.min_confidence, the result's intent is
            IntentType.UNKNOWN (confidence 0.0 for blank input; the
            model's own confidence otherwise).

        Raises:
            ArtifactNotFoundError: if no trained model artifact exists.
                Runtime inference never trains automatically -- see
                docs/ml.md ("How to train").
        """
        if not isinstance(text, str) or not text.strip():
            logger.warning("MLIntentService.predict called with empty input")
            return IntentResult(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                raw_text=text if isinstance(text, str) else "",
            )

        label, confidence = predict_intent(text, artifact_path=self._artifact_path)

        if confidence < CONFIG.ml.min_confidence:
            logger.info(
                "Prediction confidence %.3f below threshold %.3f; "
                "returning UNKNOWN",
                confidence,
                CONFIG.ml.min_confidence,
            )
            intent = IntentType.UNKNOWN
        else:
            intent = IntentType[label]

        return IntentResult(intent=intent, confidence=confidence, raw_text=text)
