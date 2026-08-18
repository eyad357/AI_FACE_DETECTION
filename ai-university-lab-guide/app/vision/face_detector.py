"""
Concrete face detection implementation.

Uses OpenCV's Haar cascade classifier, which is lightweight, dependency
-free (ships inside opencv-python) and reliable enough for a real-time
university demo. It does NOT provide a true statistical confidence
score, so DetectionResult.confidence / FaceDetection.confidence are
always None for this implementation. Do not invent fake confidence
values (see docs/integration_contract.md).

This module has no knowledge of the Robot, Decision, Guide, or UI
layers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import numpy as np

try:
    import cv2
except ImportError as exc:  # pragma: no cover - environment issue, not logic
    raise ImportError(
        "OpenCV (opencv-python) is required by app.vision.face_detector. "
        "Install project dependencies with: pip install -r requirements.txt"
    ) from exc

from app.config import CONFIG
from app.models.schemas import BoundingBox, DetectionResult, FaceDetection
from app.utils.logger import get_logger
from app.vision.detector_interface import FaceDetectorInterface

logger = get_logger(__name__)


class FaceDetector(FaceDetectorInterface):
    """
    OpenCV Haar-cascade based face detector.

    Usage:
        detector = FaceDetector()
        result = detector.detect(frame)
    """

    def __init__(self, cascade_path: Optional[str] = None) -> None:
        """
        Args:
            cascade_path: Optional path to a custom Haar cascade XML
                file. Defaults to OpenCV's bundled frontal-face cascade.

        Raises:
            RuntimeError: If the cascade file cannot be loaded. This is
                raised at construction time (once), not per frame, so
                initialization cost is paid only once (Rule 12,
                performance).
        """
        path = cascade_path or (
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self._cascade = cv2.CascadeClassifier(path)
        if self._cascade.empty():
            logger.error("Failed to load Haar cascade from %s", path)
            raise RuntimeError(f"Could not load Haar cascade classifier from: {path}")

        logger.info("FaceDetector initialized (cascade=%s)", path)

    def detect(self, frame: np.ndarray) -> DetectionResult:
        """
        Detect faces in a single BGR frame.

        Args:
            frame: BGR image as a NumPy array, shape (H, W, 3) or a
                single-channel grayscale image of shape (H, W).

        Returns:
            DetectionResult with detected/face_count/faces populated.
            confidence is always None for this Haar-cascade based
            implementation, since it does not produce a true ML
            confidence score.

        Raises:
            ValueError: If frame is None, not a NumPy array, empty, or
                has an unsupported number of dimensions.
        """
        self._validate_frame(frame)

        gray = self._to_grayscale(frame)

        raw_faces = self._cascade.detectMultiScale(
            gray,
            scaleFactor=CONFIG.vision.haar_scale_factor,
            minNeighbors=CONFIG.vision.haar_min_neighbors,
            minSize=(
                CONFIG.vision.haar_min_face_size,
                CONFIG.vision.haar_min_face_size,
            ),
        )

        timestamp = datetime.now(timezone.utc)

        if len(raw_faces) == 0:
            logger.debug("No face detected in frame")
            return DetectionResult.empty(timestamp=timestamp)

        faces = [
            FaceDetection(
                bounding_box=BoundingBox(
                    x=int(x), y=int(y), width=int(w), height=int(h)
                ),
                confidence=None,
            )
            for (x, y, w, h) in raw_faces
        ]

        logger.info("Detected %d face(s)", len(faces))

        return DetectionResult(
            detected=True,
            face_count=len(faces),
            confidence=None,
            timestamp=timestamp,
            faces=faces,
        )

    @staticmethod
    def _validate_frame(frame: np.ndarray) -> None:
        if frame is None:
            raise ValueError("frame must not be None")
        if not isinstance(frame, np.ndarray):
            raise ValueError(f"frame must be a numpy.ndarray, got {type(frame)!r}")
        if frame.size == 0:
            raise ValueError("frame must not be empty")
        if frame.ndim not in (2, 3):
            raise ValueError(
                f"frame must have 2 (grayscale) or 3 (color) dimensions, "
                f"got shape {frame.shape}"
            )
        if frame.ndim == 3 and frame.shape[2] not in (1, 3, 4):
            raise ValueError(
                f"frame with 3 dimensions must have 1, 3, or 4 channels, "
                f"got shape {frame.shape}"
            )

    @staticmethod
    def _to_grayscale(frame: np.ndarray) -> np.ndarray:
        if frame.ndim == 2:
            return frame
        channels = frame.shape[2]
        if channels == 1:
            return frame[:, :, 0]
        if channels == 4:
            return cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
