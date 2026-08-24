"""
InferenceEngine — runs a `GestureMLP` over a preprocessed frame and
produces a typed `GestureResult`.

This is the component `app.dl.service.GestureRecognitionService` (the
public API) delegates to. It owns confidence-threshold policy and all
failure handling described in docs/dl.md "Confidence and failure
handling":

- malformed/invalid input           -> DLError (raised)
- model produces a low-confidence
  prediction                        -> GestureResult(UNKNOWN, ...) (returned, not raised)
- everything else                   -> GestureResult(<label>, ...) (returned)

This module has no dependency on Vision, Robot, ML, Navigation,
Decision, Guide, or app.main.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Tuple

import numpy as np

from app.dl.inference.preprocessing import preprocess_frame
from app.dl.models.gesture_types import DLError, GestureLabel, GestureResult
from app.dl.models.network import GestureMLP
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Fixed, canonical ordering of GestureLabel members to output indices.
# This ordering is the model's contract with its own weights: index i
# in the softmax output always corresponds to _LABEL_ORDER[i]. It must
# never be reordered without retraining every artifact that depends on
# it (see docs/dl.md "Model lifecycle").
_LABEL_ORDER: Tuple[GestureLabel, ...] = (
    GestureLabel.WAVE,
    GestureLabel.STOP,
    GestureLabel.POINT,
    GestureLabel.UNKNOWN,
)


class InferenceEngine:
    """
    Wraps a `GestureMLP` with preprocessing and confidence-threshold
    policy to produce `GestureResult`s.
    """

    def __init__(
        self,
        model: GestureMLP,
        image_size: Tuple[int, int],
        confidence_threshold: float,
    ) -> None:
        if not isinstance(model, GestureMLP):
            raise DLError(
                f"InferenceEngine requires a GestureMLP, got {type(model)!r}"
            )
        if model.num_classes != len(_LABEL_ORDER):
            raise DLError(
                f"InferenceEngine requires a model with "
                f"{len(_LABEL_ORDER)} output classes (one per "
                f"GestureLabel), got {model.num_classes}. The model "
                f"artifact is malformed or was trained for a different "
                f"label set."
            )
        if not (0.0 <= confidence_threshold <= 1.0):
            raise DLError(
                "InferenceEngine.confidence_threshold must be within "
                f"[0.0, 1.0], got {confidence_threshold}"
            )
        self._model = model
        self._image_size = image_size
        self._confidence_threshold = confidence_threshold

    def predict(self, frame: np.ndarray) -> GestureResult:
        """
        Run inference on a single frame.

        Args:
            frame: A BGR/BGRA/grayscale NumPy array.

        Returns:
            A `GestureResult`. Never `None`; never a silently-wrong
            guess — a below-threshold prediction is reported as
            `GestureLabel.UNKNOWN` with the real score distribution
            attached, not hidden.

        Raises:
            DLError: for malformed/invalid input (see
                `app.dl.inference.preprocessing.preprocess_frame`).
        """
        features = preprocess_frame(frame, self._image_size)
        probs = self._model.forward(features)

        scores = {label.value: float(p) for label, p in zip(_LABEL_ORDER, probs)}
        best_index = int(np.argmax(probs))
        best_label = _LABEL_ORDER[best_index]
        best_confidence = float(probs[best_index])
        timestamp = datetime.now(timezone.utc)

        if best_confidence < self._confidence_threshold:
            logger.debug(
                "Gesture prediction %s (%.3f) below threshold %.3f -> UNKNOWN",
                best_label.value,
                best_confidence,
                self._confidence_threshold,
            )
            return GestureResult.unknown(
                reason="low_confidence",
                scores=scores,
                confidence=best_confidence,
                timestamp=timestamp,
            )

        return GestureResult(
            gesture=best_label,
            confidence=best_confidence,
            scores=scores,
            timestamp=timestamp,
            metadata={},
        )
