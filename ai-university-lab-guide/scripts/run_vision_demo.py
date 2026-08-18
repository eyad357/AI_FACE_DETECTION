#!/usr/bin/env python3
"""
Standalone Vision demo.

Proves that Person 1's Vision module works completely independently of
Robot, Decision, Guide, and UI. Opens the camera, runs face detection on
each frame, draws bounding boxes, and prints/overlays detection status.

Run:
    python scripts/run_vision_demo.py

Press 'q' in the video window to quit.

This script does NOT import app.robot, app.decision, app.guide, or
app.ui.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Allow running as `python scripts/run_vision_demo.py` from the project root
# without requiring the package to be installed.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2  # noqa: E402

from app.utils.logger import get_logger  # noqa: E402
from app.vision.camera import Camera  # noqa: E402
from app.vision.face_detector import FaceDetector  # noqa: E402

logger = get_logger(__name__)

WINDOW_TITLE = "AI University Lab Guide — Vision Demo"


def draw_overlay(frame, result, fps: float):
    """Draw bounding boxes and a status panel onto the frame in place."""
    for face in result.faces:
        box = face.bounding_box
        cv2.rectangle(
            frame,
            (box.x, box.y),
            (box.x + box.width, box.y + box.height),
            (0, 200, 0),
            2,
        )

    status = "FACE DETECTED" if result.detected else "NO FACE"
    confidence_text = (
        f"{result.confidence:.2f}" if result.confidence is not None else "N/A"
    )

    lines = [
        WINDOW_TITLE,
        f"Status: {status}",
        f"Faces: {result.face_count}",
        f"Confidence: {confidence_text}",
        f"FPS: {fps:.1f}",
    ]
    for i, line in enumerate(lines):
        cv2.putText(
            frame,
            line,
            (10, 24 + i * 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255) if i == 0 else (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
    return frame


def run() -> int:
    camera = Camera()
    if not camera.open():
        logger.error("Could not open camera. Is one connected and free?")
        print("ERROR: Could not open camera. Exiting demo.")
        return 1

    detector = FaceDetector()

    prev_time = time.time()
    fps = 0.0

    try:
        while True:
            ok, frame = camera.read()
            if not ok or frame is None:
                logger.warning("Frame read failed, stopping demo loop")
                break

            result = detector.detect(frame)

            now = time.time()
            elapsed = now - prev_time
            prev_time = now
            if elapsed > 0:
                fps = 1.0 / elapsed

            draw_overlay(frame, result, fps)
            cv2.imshow(WINDOW_TITLE, frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                logger.info("Quit key pressed, stopping demo")
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
