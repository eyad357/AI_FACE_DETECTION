"""
Detector abstraction.

The rest of the application (and the Decision layer, in the future)
should depend on this interface rather than a concrete detector
implementation. This allows FaceDetector (Haar-cascade based, see
face_detector.py) to be swapped later for another OpenCV method,
MediaPipe, or another CV model, without changing any calling code.

Kept intentionally minimal — do not overengineer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from app.models.schemas import DetectionResult


class FaceDetectorInterface(ABC):
    """Minimal contract every face detector implementation must satisfy."""

    @abstractmethod
    def detect(self, frame: np.ndarray) -> DetectionResult:
        """
        Run face detection on a single frame.

        Args:
            frame: A BGR image as a NumPy array (as produced by
                app.vision.camera.Camera.read()).

        Returns:
            A DetectionResult describing what was found. Implementations
            must return a valid DetectionResult even when no face is
            found (detected=False, face_count=0) rather than raising.

        Raises:
            ValueError: If `frame` is not a valid image (e.g. None,
                wrong number of dimensions, or empty array).
        """
        raise NotImplementedError
