"""
Vision / Perception layer.

Responsibility: observe camera frames and produce standardized
DetectionResult objects (app.models.schemas.DetectionResult).

This package MUST NOT import app.robot, app.decision, app.guide, or
app.ui. It depends only on the Python standard library, OpenCV, NumPy,
app.models, app.config, and app.utils.logger. See
docs/integration_contract.md for the full dependency rules.
"""

from app.vision.camera import Camera
from app.vision.detector_interface import FaceDetectorInterface
from app.vision.face_detector import FaceDetector

__all__ = ["Camera", "FaceDetectorInterface", "FaceDetector"]
