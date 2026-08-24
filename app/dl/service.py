"""
Public DL API — `GestureRecognitionService`.

    from app.dl.service import GestureRecognitionService

    recognizer = GestureRecognitionService()
    result = recognizer.predict(frame)   # -> GestureResult

Responsibility: "What gesture is being performed in this frame?" —
nothing more. It does NOT decide what the robot should do in response
(that is the future orchestration/integration layer's job — see
docs/dl.md "Integration boundary"). This mirrors how `app.guide` only
answers "what information should be given" and `app.decision` only
answers "what should happen next", each leaving execution to a
different layer.

Dependency rules (enforced by tests/dl/test_dependency_isolation.py):
    - MUST NOT import app.robot
    - MUST NOT import app.vision
    - MUST NOT import app.ml
    - MUST NOT import app.navigation
    - MUST NOT import app.decision (implementation)
    - MUST NOT import app.guide
    - MUST NOT import app.main
    - MAY use app.utils.logger for logging
    - Uses this package's own `app.dl.config` rather than
      `app.config`, since DL's settings are not currently consumed
      anywhere else (see `app/dl/config.py` docstring)

Only Python objects (dataclasses, enums, floats, dicts) cross this
API's boundary — no NumPy arrays or framework-specific tensors leak
out through `GestureResult` (the input `frame` itself is the one
NumPy array callers pass in, exactly like
`FaceDetectorInterface.detect(frame)` already does elsewhere in this
project).
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from app.dl.config import DL_CONFIG, DLConfig
from app.dl.inference.engine import InferenceEngine
from app.dl.models.gesture_types import DLError, GestureResult
from app.dl.models.network import GestureMLP
from app.utils.logger import get_logger

logger = get_logger(__name__)

_NUM_CLASSES = 4  # WAVE, STOP, POINT, UNKNOWN -- see gesture_types.GestureLabel


class GestureRecognitionService:
    """
    The stable, public entry point for DL gesture recognition.

    On construction, this service tries to load a real trained model
    artifact from `config.artifact_path`. If none is found:

    - `require_trained_artifact=False` (the default): falls back to an
      explicitly-untrained, deterministically-seeded `GestureMLP`
      (`GestureMLP.from_seed(...)`). Every `GestureResult` produced by
      this fallback carries `metadata["model_source"] ==
      "untrained_fixture"` so a caller can never mistake it for a real
      prediction (see docs/dl.md "Model lifecycle"). This mode exists
      so DL remains importable/constructible/independently-testable
      even before any training has been run.
    - `require_trained_artifact=True`: raises `DLError` instead — for
      deployments that must fail loudly rather than silently degrade.

    A caller may also supply an already-loaded `GestureMLP` directly
    (e.g. one loaded from a custom path, or a model trained on a real
    dataset), bypassing artifact-path resolution entirely.
    """

    def __init__(
        self,
        model: Optional[GestureMLP] = None,
        config: Optional[DLConfig] = None,
        require_trained_artifact: bool = False,
    ) -> None:
        self._config = config or DL_CONFIG
        self._model_source: str

        if model is not None:
            self._model = model
            self._model_source = "caller_provided"
        else:
            try:
                self._model = GestureMLP.load(self._config.artifact_path)
                self._model_source = "trained_artifact"
                logger.info(
                    "Loaded DL gesture model from %s", self._config.artifact_path
                )
            except DLError as exc:
                if require_trained_artifact:
                    raise DLError(
                        f"No trained DL model artifact available at "
                        f"{self._config.artifact_path} and "
                        f"require_trained_artifact=True: {exc}"
                    ) from exc
                logger.warning(
                    "No trained DL model artifact at %s (%s); falling back "
                    "to an untrained, deterministically-seeded fixture "
                    "model. Predictions from this fallback are NOT "
                    "meaningful gesture recognition -- see docs/dl.md.",
                    self._config.artifact_path,
                    exc,
                )
                self._model = GestureMLP.from_seed(
                    input_dim=self._config.input_dim,
                    hidden_dim=self._config.hidden_size,
                    num_classes=_NUM_CLASSES,
                    seed=self._config.default_seed,
                )
                self._model_source = "untrained_fixture"

        self._engine = InferenceEngine(
            model=self._model,
            image_size=self._config.image_size,
            confidence_threshold=self._config.confidence_threshold,
        )

    def predict(self, frame: np.ndarray) -> GestureResult:
        """
        Recognize the gesture in a single frame.

        Args:
            frame: A BGR, BGRA, or grayscale NumPy array (any source —
                DL does not own frame capture; see docs/dl.md
                "Dependency inversion").

        Returns:
            A `GestureResult`. If this service is running on the
            untrained fixture fallback, every result additionally has
            `metadata["model_source"] == "untrained_fixture"`.

        Raises:
            DLError: for malformed/invalid input (None, wrong type,
                wrong shape, empty frame).
        """
        result = self._engine.predict(frame)
        if self._model_source == "untrained_fixture":
            merged_metadata = dict(result.metadata)
            merged_metadata["model_source"] = self._model_source
            result = GestureResult(
                gesture=result.gesture,
                confidence=result.confidence,
                scores=result.scores,
                timestamp=result.timestamp,
                metadata=merged_metadata,
            )
        return result

    @property
    def model_source(self) -> str:
        """
        One of "trained_artifact", "untrained_fixture", or
        "caller_provided" — where this service's model came from.
        """
        return self._model_source

    @property
    def model_info(self) -> dict:
        """Small, framework-independent summary of the loaded model."""
        return {
            "model_source": self._model_source,
            "input_dim": self._model.input_dim,
            "hidden_dim": self._model.hidden_dim,
            "num_classes": self._model.num_classes,
            "num_params": self._model.num_params,
            "confidence_threshold": self._config.confidence_threshold,
        }
