"""Shared, framework-independent data contracts used across the whole app."""

from app.models.schemas import BoundingBox, DetectionResult, FaceDetection

__all__ = ["BoundingBox", "DetectionResult", "FaceDetection"]
