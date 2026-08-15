"""
Centralized, typed configuration for the AI University Lab Guide Robot.

All configurable values used anywhere in the application must live here.
No module should hard-code its own copies of these values or read
environment-specific paths directly.

Values can be overridden via environment variables (useful for CI, other
machines, or a different camera index) without touching code.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class CameraConfig:
    """Settings for the camera abstraction (app.vision.camera)."""

    index: int = _env_int("LABGUIDE_CAMERA_INDEX", 0)
    width: int = _env_int("LABGUIDE_CAMERA_WIDTH", 640)
    height: int = _env_int("LABGUIDE_CAMERA_HEIGHT", 480)
    fps: int = _env_int("LABGUIDE_CAMERA_FPS", 30)


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


@dataclass(frozen=True)
class LoggingConfig:
    """Settings for app.utils.logger."""

    level: str = _env_str("LABGUIDE_LOG_LEVEL", "INFO")
    format: str = _env_str(
        "LABGUIDE_LOG_FORMAT",
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )


@dataclass(frozen=True)
class AppConfig:
    """Top-level configuration bundle for the whole application."""

    camera: CameraConfig = CameraConfig()
    vision: VisionConfig = VisionConfig()
    logging: LoggingConfig = LoggingConfig()


# Single shared configuration instance. Import this rather than
# instantiating the dataclasses directly, so the whole application uses
# one consistent, centralized configuration.
CONFIG = AppConfig()
