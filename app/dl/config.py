"""
Centralized, typed configuration for the DL (Deep Learning) gesture
recognition subsystem.

This module deliberately does NOT modify `app/config.py`. That file is
a protected, frozen component (see `docs/contracts.md`), and — per its
own trailing note — a new configuration section should only be added
there once a module has a genuine, shared need for it. DL's
configuration needs are internal to DL (artifact path, image size,
confidence threshold) and are not consumed anywhere else, so they live
here, following the exact same pattern `app/config.py` already uses
(frozen dataclass + `LABGUIDE_*`-prefixed environment overrides +
`__post_init__` validation) so it is trivial to fold into
`app/config.py` later if a genuine cross-module need ever appears.

DL MUST NOT import `app.robot`, `app.vision`, `app.ml`, `app.navigation`,
`app.decision` (implementation), `app.guide`, or `app.main` — see
`docs/dl.md` and `docs/contracts.md`. This module depends only on the
Python standard library.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple


class DLConfigurationError(ValueError):
    """Raised when a DL configuration value is invalid or unparsable."""


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        raise DLConfigurationError(
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
        raise DLConfigurationError(
            f"Invalid value for environment variable {name}={raw!r}: "
            f"expected a floating-point number."
        ) from None


def _env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


# Directory this file lives in: app/dl/. The default artifact path is
# resolved relative to it so DL works from any current working
# directory, exactly like app.ml.artifacts is documented to.
_DL_PACKAGE_DIR = Path(__file__).resolve().parent
_DEFAULT_ARTIFACT_PATH = str(
    _DL_PACKAGE_DIR / "artifacts" / "gesture_mlp_fixture.npz"
)


@dataclass(frozen=True)
class DLConfig:
    """Settings for the gesture-recognition subsystem (app.dl)."""

    # Where GestureRecognitionService loads its default model artifact
    # from. See docs/dl.md for the artifact format and provenance.
    artifact_path: str = _env_str("LABGUIDE_DL_ARTIFACT_PATH", _DEFAULT_ARTIFACT_PATH)

    # Preprocessing target size (width, height) that every input frame
    # is normalized to before inference. Kept small deliberately: this
    # is a lightweight, CPU-only, deterministic model, not a full CNN.
    image_width: int = _env_int("LABGUIDE_DL_IMAGE_WIDTH", 20)
    image_height: int = _env_int("LABGUIDE_DL_IMAGE_HEIGHT", 20)

    # Hidden layer width of the gesture MLP.
    hidden_size: int = _env_int("LABGUIDE_DL_HIDDEN_SIZE", 24)

    # Minimum softmax confidence required to report a concrete gesture
    # rather than GestureLabel.UNKNOWN. See docs/dl.md "Confidence
    # semantics".
    confidence_threshold: float = _env_float(
        "LABGUIDE_DL_CONFIDENCE_THRESHOLD", 0.5
    )

    # Deterministic seed used when no trained artifact is available and
    # GestureRecognitionService falls back to an explicitly-untrained
    # fixture model (see service.py). Also the default seed used by the
    # training pipeline's fixture dataset generator.
    default_seed: int = _env_int("LABGUIDE_DL_DEFAULT_SEED", 0)

    def __post_init__(self) -> None:
        if self.image_width <= 0 or self.image_height <= 0:
            raise DLConfigurationError(
                "DLConfig.image_width/image_height must be > 0, got "
                f"width={self.image_width}, height={self.image_height}"
            )
        if self.hidden_size <= 0:
            raise DLConfigurationError(
                f"DLConfig.hidden_size must be > 0, got {self.hidden_size}"
            )
        if not (0.0 <= self.confidence_threshold <= 1.0):
            raise DLConfigurationError(
                "DLConfig.confidence_threshold must be within [0.0, 1.0], "
                f"got {self.confidence_threshold}"
            )

    @property
    def image_size(self) -> Tuple[int, int]:
        """(width, height) target size used by preprocessing."""
        return (self.image_width, self.image_height)

    @property
    def input_dim(self) -> int:
        """Flattened, grayscale input feature dimensionality."""
        return self.image_width * self.image_height


# Single shared configuration instance. Import this rather than
# instantiating DLConfig directly, mirroring app.config.CONFIG.
DL_CONFIG = DLConfig()
