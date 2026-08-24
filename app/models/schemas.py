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
from enum import Enum
from typing import List, Optional, Tuple


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


class IntentType(Enum):
    """
    Typed student-question intents produced by the ML intent classifier
    (app.ml.service).

    These describe WHAT a student is asking for — nothing more. Deciding
    what to do about an intent (route to Guide, Navigation, both, or a
    help response) remains a future orchestration-layer responsibility,
    not ML's.
    """

    INFORMATION = "INFORMATION"
    NAVIGATION = "NAVIGATION"
    COMBINED = "COMBINED"
    HELP = "HELP"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class IntentResult:
    """
    Canonical output of the ML intent classifier for a single student
    question.

    This is the ONLY IntentResult definition in the project. Do not
    duplicate this structure elsewhere.

    Attributes:
        intent: The predicted intent.
        confidence: Model confidence in the range [0.0, 1.0].
        raw_text: The original, unmodified input text that was
            classified (kept for traceability/debugging, not for
            re-processing by consumers).
    """

    intent: IntentType
    confidence: float
    raw_text: str

    def __post_init__(self) -> None:
        if not isinstance(self.intent, IntentType):
            raise ValueError(
                f"IntentResult.intent must be an IntentType, got "
                f"{type(self.intent).__name__}"
            )
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"IntentResult.confidence must be within [0.0, 1.0], got "
                f"{self.confidence}"
            )
        if not isinstance(self.raw_text, str):
            raise ValueError(
                f"IntentResult.raw_text must be a str, got "
                f"{type(self.raw_text).__name__}"
            )


class GestureType(Enum):
    """
    Physical gesture classes produced by the DL gesture recognizer
    (app.dl.service).

    These describe WHAT gesture was performed -- nothing more. Deciding
    what the robot should do about it (greet, stop, navigate, speak)
    remains a future orchestration-layer responsibility, not DL's.
    """

    WAVE = "WAVE"
    STOP = "STOP"
    POINT = "POINT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class GestureResult:
    """
    Canonical output of the DL gesture recognizer for a single processed
    input.

    This is the ONLY GestureResult definition in the project. Do not
    duplicate this structure elsewhere.

    Attributes:
        gesture: The predicted gesture.
        confidence: Model confidence in the range [0.0, 1.0].
        timestamp: UTC time the recognition was produced.
    """

    gesture: GestureType
    confidence: float
    timestamp: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.gesture, GestureType):
            raise ValueError(
                f"GestureResult.gesture must be a GestureType, got "
                f"{type(self.gesture).__name__}"
            )
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"GestureResult.confidence must be within [0.0, 1.0], got "
                f"{self.confidence}"
            )
        if not isinstance(self.timestamp, datetime):
            raise ValueError(
                f"GestureResult.timestamp must be a datetime, got "
                f"{type(self.timestamp).__name__}"
            )


class Capability(Enum):
    """
    System capabilities a request may require, as determined by
    app.context.service from an IntentResult.

    These name WHICH capability modules are needed to fulfill a
    request -- nothing more. Actually invoking Navigation or Guide is a
    future orchestration-layer (main.py) responsibility, not
    app.context's.
    """

    NAVIGATION = "NAVIGATION"
    GUIDE = "GUIDE"


@dataclass(frozen=True)
class RequestPlan:
    """
    Canonical output of app.context.service for a single IntentResult:
    which capabilities (if any) are required to fulfill the request.

    This is the ONLY RequestPlan definition in the project. Do not
    duplicate this structure elsewhere.

    Attributes:
        intent: The IntentType this plan was derived from (carried
            through for traceability).
        required_capabilities: The capabilities needed to fulfill the
            request, in a stable, deterministic order. Empty for
            intents that need no capability module (HELP) or that
            could not be planned for (UNKNOWN).
        supported: Whether this intent has a defined plan. True for
            INFORMATION, NAVIGATION, COMBINED, and HELP; False for
            UNKNOWN (and any other value that is not a recognized,
            planned intent).
        reason: A short, human-readable note -- always set when
            supported is False (why no plan exists), and may also be
            set for HELP (why it needs no capability).
    """

    intent: IntentType
    required_capabilities: Tuple[Capability, ...] = ()
    supported: bool = True
    reason: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.intent, IntentType):
            raise ValueError(
                f"RequestPlan.intent must be an IntentType, got "
                f"{type(self.intent).__name__}"
            )
        if not isinstance(self.required_capabilities, tuple) or any(
            not isinstance(cap, Capability) for cap in self.required_capabilities
        ):
            raise ValueError(
                "RequestPlan.required_capabilities must be a tuple of Capability"
            )
        if not isinstance(self.supported, bool):
            raise ValueError(
                f"RequestPlan.supported must be a bool, got "
                f"{type(self.supported).__name__}"
            )
        if self.reason is not None and not isinstance(self.reason, str):
            raise ValueError(
                f"RequestPlan.reason must be a str or None, got "
                f"{type(self.reason).__name__}"
            )
        if not self.supported and not self.reason:
            raise ValueError("RequestPlan.reason must be set when supported is False")


@dataclass(frozen=True)
class CombinedResponse:
    """
    Structural container for a COMBINED request's results, once a
    future orchestration layer has invoked both Navigation and Guide.

    This is the ONLY CombinedResponse definition in the project. Do not
    duplicate this structure elsewhere.

    app.context never constructs a populated CombinedResponse itself --
    doing so would require calling Navigation and Guide, which
    app.context is explicitly forbidden from doing. This contract only
    defines the SHAPE that future integration (main.py) will fill in.

    Attributes:
        navigation_result: The Navigation branch's result, or None if
            Navigation was not attempted. Deliberately left untyped
            (not app.navigation.contracts.RouteResult): app.context
            must not import app.navigation, so it cannot reference
            that type -- the same reasoning already applied to
            guide_response below. Navigation's real, canonical result
            type is app.navigation.contracts.RouteResult (see
            NavigationService.find_route()); whatever object is placed
            here is opaque to app.context and app.models -- only the
            future integration layer that actually calls Navigation
            constructs and interprets it. (An earlier revision of this
            file defined a separate, schemas-owned NavigationResult
            dataclass here; it was never produced by
            NavigationService.find_route(), which returns RouteResult,
            so it was a stale, unused duplicate contract and has been
            removed -- see docs/navigation.md and
            app/navigation/contracts.py for the real contract.)
        guide_response: The Guide branch's result, or None if Guide was
            not attempted. Deliberately left untyped (not
            app.guide.GuideResponse): app.context must not import
            app.guide, so it cannot reference that type. Whatever
            object is placed here is opaque to app.context -- only the
            future integration layer that actually calls Guide
            interprets its contents.

    Each field is independent: a missing/failed result on one side
    never discards or invalidates a successful result on the other
    (see docs/context.md, "Combined request behavior").
    """

    navigation_result: Optional[object] = None
    guide_response: Optional[object] = None
