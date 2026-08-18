"""
Camera lifecycle abstraction.

Responsibility: open/read/release a camera device and expose a clean,
OpenCV-agnostic API to the rest of the application. This module does
NOT perform any face detection or higher-level perception — see
face_detector.py for that.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

try:
    import cv2
except ImportError as exc:  # pragma: no cover - environment issue, not logic
    raise ImportError(
        "OpenCV (opencv-python) is required by app.vision.camera. "
        "Install project dependencies with: pip install -r requirements.txt"
    ) from exc

from app.config import CONFIG
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CameraError(RuntimeError):
    """Raised for camera-related failures that the caller should handle."""


class Camera:
    """
    Thin, testable wrapper around cv2.VideoCapture.

    Usage:
        camera = Camera()
        if camera.open():
            ok, frame = camera.read()
            ...
        camera.release()

    The class can also be used as a context manager:
        with Camera() as camera:
            ok, frame = camera.read()
    """

    def __init__(
        self,
        index: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> None:
        """
        Args:
            index: Camera device index. Defaults to app.config CONFIG.camera.index.
            width: Requested capture width. Defaults to app.config CONFIG.camera.width.
            height: Requested capture height. Defaults to app.config CONFIG.camera.height.
        """
        self._index = index if index is not None else CONFIG.camera.index
        self._width = width if width is not None else CONFIG.camera.width
        self._height = height if height is not None else CONFIG.camera.height
        self._capture: Optional["cv2.VideoCapture"] = None

    @property
    def is_opened(self) -> bool:
        """True if the underlying device is currently open and usable."""
        return self._capture is not None and bool(self._capture.isOpened())

    def open(self) -> bool:
        """
        Open the camera device.

        Returns:
            True if the camera opened successfully, False otherwise. This
            method never raises for a simply-unavailable camera; callers
            should check the return value (or is_opened) and handle the
            False case gracefully (Rule: Vision must fail gracefully).
        """
        logger.debug("Opening camera at index=%s", self._index)
        try:
            capture = cv2.VideoCapture(self._index)
        except Exception:  # pragma: no cover - defensive, backend-specific
            logger.error("Exception while creating VideoCapture(index=%s)", self._index)
            self._capture = None
            return False

        if not capture.isOpened():
            logger.warning("Camera at index=%s is unavailable", self._index)
            capture.release()
            self._capture = None
            return False

        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)

        self._capture = capture
        logger.info(
            "Camera opened (index=%s, requested=%sx%s)",
            self._index,
            self._width,
            self._height,
        )
        return True

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Read a single frame from the camera.

        Returns:
            (True, frame) on success, (False, None) if the camera is not
            open or the read failed. Never raises for a normal read
            failure.
        """
        if not self.is_opened:
            logger.warning("read() called but camera is not open")
            return False, None

        ok, frame = self._capture.read()
        if not ok or frame is None:
            logger.warning("Failed to read a frame from the camera")
            return False, None

        return True, frame

    def release(self) -> None:
        """Release the camera device. Safe to call multiple times."""
        if self._capture is not None:
            self._capture.release()
            logger.info("Camera released (index=%s)", self._index)
        self._capture = None

    def __enter__(self) -> "Camera":
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()
