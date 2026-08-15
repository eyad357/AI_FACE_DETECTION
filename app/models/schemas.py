"""
Canonical shared data contracts for the AI University Lab Guide Robot.

This module is the SINGLE SOURCE OF TRUTH for cross-module data
structures. Every module (Vision, Decision, Robot, Guide, UI) that needs
to exchange perception or application data MUST import the models from
here rather than defining its own copies.

Dependency direction (see docs/integration_contract.md):

    Vision   -> app.models.schemas
    Decision -> app.models.schemas
    Robot    -> app.models.schemas
    Guide    -> app.models.schemas
    UI       -> app.models.schemas

This module MUST NOT import from app.vision, app.robot, app.decision,
app.guide, or app.ui. It has no dependencies other than the Python
standard library, which keeps it safe to import from anywhere in the
application without creating circular imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


@dataclass(frozen=True)
class BoundingBox:
    """
    Framework-independent rectangle describing where a face was found
    in an image, expressed in pixel coordinates of the source frame.

    Attributes:
        x: Left edge of the box, in pixels (>= 0).
        y: Top edge of the box, in pixels (>= 0).
        width: Width of the box, in pixels (> 0).
        height: Height of the box, in pixels (> 0).
    """

    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.x < 0 or self.y < 0:
            raise ValueError(
                f"BoundingBox coordinates must be non-negative, got "
                f"x={self.x}, y={self.y}"
            )
        if self.width <= 0 or self.height <= 0:
            raise ValueError(
                f"BoundingBox width/height must be positive, got "
                f"width={self.width}, height={self.height}"
            )

    @property
    def area(self) -> int:
        """Area of the bounding box in square pixels."""
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        """(x, y) coordinates of the box center."""
        return (self.x + self.width / 2.0, self.y + self.height / 2.0)


@dataclass(frozen=True)
class FaceDetection:
    """
    A single detected face.

    Attributes:
        bounding_box: Location of the face within the source frame.
        confidence: Detection confidence in the range [0.0, 1.0], if the
            underlying detector genuinely provides one. Detectors that do
            not produce a true confidence score (e.g. classic Haar
            cascades) MUST leave this as None rather than inventing a
            value. Consumers must treat None as "not available", not as
            zero confidence.
    """

    bounding_box: BoundingBox
    confidence: Optional[float] = None

    def __post_init__(self) -> None:
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"FaceDetection confidence must be within [0.0, 1.0] or "
                f"None, got {self.confidence}"
            )


@dataclass(frozen=True)
class DetectionResult:
    """
    Canonical output of the Vision layer for a single processed frame.

    This is the ONLY DetectionResult definition in the project. Do not
    duplicate this structure elsewhere (see Rule 3 in the integration
    contract).

    Attributes:
        detected: True if at least one face was found in the frame.
        face_count: Number of faces found (0 when detected is False).
        confidence: Overall/best confidence for the frame, if genuinely
            available from the detector. None when the detector cannot
            produce a true confidence score, or when no faces were found.
        timestamp: UTC time the detection was produced.
        faces: Per-face detection details. Empty when detected is False.
    """

    detected: bool
    face_count: int
    confidence: Optional[float]
    timestamp: datetime
    faces: List[FaceDetection] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.face_count < 0:
            raise ValueError(
                f"face_count cannot be negative, got {self.face_count}"
            )
        if self.detected and self.face_count == 0:
            raise ValueError(
                "detected=True requires face_count > 0"
            )
        if not self.detected and self.face_count != 0:
            raise ValueError(
                "detected=False requires face_count == 0"
            )
        if len(self.faces) != self.face_count:
            raise ValueError(
                f"len(faces)={len(self.faces)} does not match "
                f"face_count={self.face_count}"
            )
        if self.confidence is not None and not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"confidence must be within [0.0, 1.0] or None, got "
                f"{self.confidence}"
            )

    @staticmethod
    def empty(timestamp: Optional[datetime] = None) -> "DetectionResult":
        """Convenience constructor for a 'no face detected' result."""
        return DetectionResult(
            detected=False,
            face_count=0,
            confidence=None,
            timestamp=timestamp or datetime.now(timezone.utc),
            faces=[],
        )
