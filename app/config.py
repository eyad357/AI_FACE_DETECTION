"""
Centralized, typed configuration for the AI University Lab Guide Robot.

All configurable values used anywhere in the application must live here.
No module should hard-code its own copies of these values or read
environment-specific paths directly.

Values can be overridden via environment variables (useful for CI, other
machines, or a different camera index) without touching code.

Configuration provides settings; it does not orchestrate modules. Module
orchestration remains the sole responsibility of app.main.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

_VALID_LOG_LEVEL_NAMES = frozenset(
    {"CRITICAL", "FATAL", "ERROR", "WARNING", "WARN", "INFO", "DEBUG", "NOTSET"}
)


class ConfigurationError(ValueError):
    """
    Raised when a configuration value is invalid.

    This covers two distinct situations, both reported explicitly rather
    than silently falling back to a default:

    1. An environment variable is set but cannot be parsed as the
       expected type (e.g. LABGUIDE_CAMERA_INDEX=abc).
    2. A configuration value (from the environment or an explicit
       constructor argument) is out of its valid range (e.g. a negative
       camera index, or a confidence threshold outside [0.0, 1.0]).

    An unset or empty environment variable is NOT an error — that
    legitimately falls back to the documented default.
    """


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        raise ConfigurationError(
            f"Invalid value for environment variable {name}={raw!r}: "
            f"expected an integer."
        ) from None


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        raise ConfigurationError(
            f"Invalid value for environment variable {name}={raw!r}: "
            f"expected a floating-point number."
        ) from None


def _env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class CameraConfig:
    """Settings for the camera abstraction (app.vision.camera)."""

    index: int = _env_int("LABGUIDE_CAMERA_INDEX", 0)
    width: int = _env_int("LABGUIDE_CAMERA_WIDTH", 640)
    height: int = _env_int("LABGUIDE_CAMERA_HEIGHT", 480)
    fps: int = _env_int("LABGUIDE_CAMERA_FPS", 30)

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ConfigurationError(
                f"CameraConfig.index must be >= 0, got {self.index}"
            )
        if self.width <= 0:
            raise ConfigurationError(
                f"CameraConfig.width must be > 0, got {self.width}"
            )
        if self.height <= 0:
            raise ConfigurationError(
                f"CameraConfig.height must be > 0, got {self.height}"
            )
        if self.fps <= 0:
            raise ConfigurationError(
                f"CameraConfig.fps must be > 0, got {self.fps}"
            )


@dataclass(frozen=True)
class VisionConfig:
    """Settings for the face detection pipeline (app.vision)."""

    # Minimum confidence required to treat a detection as valid, for
    # detector implementations that genuinely provide a confidence score.
    face_confidence_threshold: float = _env_float(
        "LABGUIDE_FACE_CONFIDENCE_THRESHOLD", 0.5
    )

    # Reserved for the future temporal-stability logic in the Decision
    # layer: how many consecutive frames a face must be present in
    # before it is considered a stable "visitor". Vision does not use
    # this value itself; it only publishes it for consumers.
    detection_frames_required: int = _env_int(
        "LABGUIDE_DETECTION_FRAMES_REQUIRED", 5
    )

    # Haar cascade minimum neighbor / scale factor parameters, exposed so
    # they are not hard-coded inside the detector implementation.
    haar_scale_factor: float = _env_float("LABGUIDE_HAAR_SCALE_FACTOR", 1.1)
    haar_min_neighbors: int = _env_int("LABGUIDE_HAAR_MIN_NEIGHBORS", 5)
    haar_min_face_size: int = _env_int("LABGUIDE_HAAR_MIN_FACE_SIZE", 30)

    def __post_init__(self) -> None:
        if not (0.0 <= self.face_confidence_threshold <= 1.0):
            raise ConfigurationError(
                "VisionConfig.face_confidence_threshold must be within "
                f"[0.0, 1.0], got {self.face_confidence_threshold}"
            )
        if self.detection_frames_required <= 0:
            raise ConfigurationError(
                "VisionConfig.detection_frames_required must be > 0, got "
                f"{self.detection_frames_required}"
            )
        if self.haar_scale_factor <= 1.0:
            # cv2.CascadeClassifier.detectMultiScale requires scaleFactor
            # > 1.0; a value at or below 1.0 causes a runtime failure
            # inside FaceDetector.detect(), so this is caught here
            # centrally rather than surfacing as a confusing Vision error.
            raise ConfigurationError(
                "VisionConfig.haar_scale_factor must be > 1.0, got "
                f"{self.haar_scale_factor}"
            )
        if self.haar_min_neighbors < 0:
            raise ConfigurationError(
                "VisionConfig.haar_min_neighbors must be >= 0, got "
                f"{self.haar_min_neighbors}"
            )
        if self.haar_min_face_size <= 0:
            raise ConfigurationError(
                "VisionConfig.haar_min_face_size must be > 0, got "
                f"{self.haar_min_face_size}"
            )


@dataclass(frozen=True)
class LoggingConfig:
    """Settings for app.utils.logger."""

    level: str = _env_str("LABGUIDE_LOG_LEVEL", "INFO")
    format: str = _env_str(
        "LABGUIDE_LOG_FORMAT",
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    def __post_init__(self) -> None:
        if self.level.upper() not in _VALID_LOG_LEVEL_NAMES:
            raise ConfigurationError(
                f"LoggingConfig.level={self.level!r} is not a recognized "
                f"logging level (expected one of "
                f"{sorted(_VALID_LOG_LEVEL_NAMES)})"
            )
        if not self.format.strip():
            raise ConfigurationError(
                "LoggingConfig.format must not be empty"
            )


@dataclass(frozen=True)
class DecisionConfig:
    """
    Settings for the Decision layer (app.decision).

    Note: VisionConfig.detection_frames_required already exists and is
    published by Vision for future consumers, but Vision does not use it
    itself. Decision reads that existing value directly (see
    state_manager.py) rather than duplicating it here.
    """

    # Consecutive frames with detected=False required before Decision
    # considers the visitor gone (debounces momentary missed detections).
    visitor_lost_frames_required: int = _env_int(
        "LABGUIDE_VISITOR_LOST_FRAMES_REQUIRED", 5
    )

    # Seconds to remain in COOLDOWN after a session completes before a
    # newly-arriving visitor can trigger another greeting.
    greeting_cooldown_seconds: float = _env_float(
        "LABGUIDE_GREETING_COOLDOWN_SECONDS", 10.0
    )

    def __post_init__(self) -> None:
        if self.visitor_lost_frames_required <= 0:
            raise ConfigurationError(
                "DecisionConfig.visitor_lost_frames_required must be > 0, "
                f"got {self.visitor_lost_frames_required}"
            )
        if self.greeting_cooldown_seconds < 0:
            raise ConfigurationError(
                "DecisionConfig.greeting_cooldown_seconds must be >= 0, "
                f"got {self.greeting_cooldown_seconds}"
            )


# NOTE ON ROBOT / GUIDE CONFIGURATION:
# As of this phase, neither app.robot nor app.guide reads any value from
# CONFIG (verified by inspection: no `CONFIG.` reference exists in either
# package). Per the project's configuration principle ("every new setting
# must have a clear reason" / "do not invent robot-specific settings" /
# "do not add Guide settings just for completeness"), no RobotConfig or
# GuideConfig section has been added. If either module gains a genuine
# configuration need, a dedicated section should be added here at that
# time, following the same pattern as CameraConfig/VisionConfig above.


@dataclass(frozen=True)
class AppConfig:
    """Top-level configuration bundle for the whole application."""

    camera: CameraConfig = CameraConfig()
    vision: VisionConfig = VisionConfig()
    logging: LoggingConfig = LoggingConfig()
    decision: DecisionConfig = DecisionConfig()


# Single shared configuration instance. Import this rather than
# instantiating the dataclasses directly, so the whole application uses
# one consistent, centralized configuration.
CONFIG = AppConfig()
