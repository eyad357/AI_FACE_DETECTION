"""
Vision adapter for the dashboard.

Wraps app.vision.camera.Camera and app.vision.face_detector.FaceDetector
(via app.vision.detector_interface.FaceDetectorInterface). Never
fabricates a detection: if the camera cannot be opened, that is
reported honestly rather than substituted with sample data.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from app.models.schemas import DetectionResult
from app.ui.dashboard_view_models import HealthState, PerceptionPanelView, SubsystemStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VisionAdapter:
    """Dashboard-facing wrapper around the real Vision subsystem."""

    def status(self) -> SubsystemStatus:
        """
        Report Vision's health without holding a camera device open
        for the lifetime of the dashboard (reliability requirement:
        do not repeatedly/permanently occupy hardware). This performs
        a lightweight import/construct check plus a single best-effort
        camera open/release probe.
        """
        try:
            from app.vision.camera import Camera
            from app.vision.face_detector import FaceDetector

            FaceDetector()  # construction only; no frame processed
        except Exception as exc:  # pragma: no cover - environment dependent
            logger.warning("Vision unavailable: %s", exc)
            return SubsystemStatus(
                name="Vision",
                state=HealthState.UNAVAILABLE,
                detail=f"Vision could not be initialized: {exc}",
            )

        try:
            camera = Camera()
            opened = camera.open()
            camera.release()
        except Exception as exc:  # pragma: no cover - environment dependent
            return SubsystemStatus(
                name="Vision",
                state=HealthState.DEGRADED,
                detail=f"Detector ready, camera probe failed: {exc}",
            )

        if opened:
            return SubsystemStatus(name="Vision", state=HealthState.PASS, detail="Camera available")
        return SubsystemStatus(
            name="Vision",
            state=HealthState.DEGRADED,
            detail="Detector ready, but no camera device is available in this environment",
        )

    def capture_and_detect(self) -> PerceptionPanelView:
        """
        Open the camera, read one frame, run real face detection, and
        release the camera immediately. Returns an honest
        "camera unavailable" view rather than a fabricated detection
        when no camera exists (e.g. in this demo/server environment).
        """
        try:
            from app.vision.camera import Camera
            from app.vision.face_detector import FaceDetector
        except Exception as exc:  # pragma: no cover - environment dependent
            return PerceptionPanelView(
                camera_available=False,
                unavailable_reason=f"Vision could not be initialized: {exc}",
            )

        camera = Camera()
        try:
            if not camera.open():
                return PerceptionPanelView(
                    camera_available=False,
                    unavailable_reason="No camera device detected in this environment.",
                )

            ok, frame = camera.read()
            if not ok or frame is None:
                return PerceptionPanelView(
                    camera_available=True,
                    unavailable_reason="Camera opened but no frame could be read.",
                )

            detector = FaceDetector()
            result: DetectionResult = detector.detect(frame)
            return PerceptionPanelView(
                camera_available=True,
                detected=result.detected,
                face_count=result.face_count,
                confidence=result.confidence,
                timestamp=result.timestamp,
                frame=frame,
            )
        finally:
            camera.release()

    def detect_in_frame(self, frame: np.ndarray) -> PerceptionPanelView:
        """
        Run the real FaceDetector directly against an already-captured
        frame, bypassing only Camera's device-open step (the frame
        already came from a real capture -- e.g. Streamlit's
        browser-side ``st.camera_input``, which shows a genuine live
        viewfinder in the presenter's browser, something a headless
        server-side ``cv2.VideoCapture`` grab cannot guarantee). This
        never fabricates a detection: the same real
        app.vision.face_detector.FaceDetector used by
        capture_and_detect() is used here.
        """
        try:
            from app.vision.face_detector import FaceDetector
        except Exception as exc:  # pragma: no cover - environment dependent
            return PerceptionPanelView(
                camera_available=False,
                unavailable_reason=f"Vision could not be initialized: {exc}",
            )

        try:
            detector = FaceDetector()
            result: DetectionResult = detector.detect(frame)
        except Exception as exc:
            logger.warning("Detection failed on captured photo: %s", exc)
            return PerceptionPanelView(
                camera_available=True,
                unavailable_reason=f"Could not process the captured photo: {exc}",
                frame=frame,
            )

        return PerceptionPanelView(
            camera_available=True,
            detected=result.detected,
            face_count=result.face_count,
            confidence=result.confidence,
            timestamp=result.timestamp,
            frame=frame,
        )
