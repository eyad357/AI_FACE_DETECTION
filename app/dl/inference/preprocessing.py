"""
Frame preprocessing for gesture inference.

Converts a caller-provided image frame into the fixed-size, flattened,
normalized feature vector `GestureMLP` expects. Implemented in pure
NumPy (no OpenCV dependency) so it is:

- deterministic: identical input always produces bit-identical output,
  with no dependency on an external library's interpolation
  implementation or version;
- dependency-light: DL does not need `app.vision.camera` or any
  OpenCV-specific decoding step to run — callers may hand it any
  BGR/grayscale NumPy array from any source (see docs/dl.md
  "Dependency inversion / caller-provided data").

Accepted input follows the same convention as
`app.vision.detector_interface.FaceDetectorInterface.detect()`: a BGR
image as a NumPy array, OR a single-channel grayscale array. DL does
NOT import `app.vision` to reuse this convention — it is duplicated
intentionally, in the same spirit `app.robot.gesture_definitions`
duplicates nothing from `app.robot.robot_commands` but stays
compatible with it by convention, not by import.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np

from app.dl.models.gesture_types import DLError

# Standard ITU-R BT.601 luma weights for BGR -> grayscale, applied in
# BGR channel order (matches OpenCV's own BGR convention used
# elsewhere in this project, e.g. app.vision.camera).
_BGR_LUMA_WEIGHTS = np.array([0.114, 0.587, 0.299], dtype=np.float32)


def _validate_frame(frame: object) -> np.ndarray:
    if frame is None:
        raise DLError("preprocess_frame() received None; a frame is required")
    if not isinstance(frame, np.ndarray):
        raise DLError(
            f"preprocess_frame() expects a numpy array, got {type(frame)!r}"
        )
    if frame.ndim not in (2, 3):
        raise DLError(
            f"preprocess_frame() expects a 2-D (grayscale) or 3-D (color) "
            f"array, got shape {frame.shape}"
        )
    if frame.ndim == 3 and frame.shape[2] not in (1, 3, 4):
        raise DLError(
            f"preprocess_frame() expects 1, 3, or 4 channels, got "
            f"shape {frame.shape}"
        )
    if frame.size == 0 or 0 in frame.shape:
        raise DLError("preprocess_frame() received an empty frame")
    return frame


def to_grayscale(frame: np.ndarray) -> np.ndarray:
    """
    Convert a validated BGR/BGRA/grayscale frame to a 2-D float32
    grayscale array in [0, 255].
    """
    if frame.ndim == 2:
        return frame.astype(np.float32)
    channels = frame.shape[2]
    if channels == 1:
        return frame[:, :, 0].astype(np.float32)
    # BGR or BGRA: use only the first 3 (B, G, R) channels.
    bgr = frame[:, :, :3].astype(np.float32)
    return bgr @ _BGR_LUMA_WEIGHTS


def resize_grayscale(gray: np.ndarray, size: Tuple[int, int]) -> np.ndarray:
    """
    Deterministically resize a 2-D float array to `size` = (width,
    height) using nearest-neighbor sampling.

    Nearest-neighbor is used deliberately instead of interpolation: it
    is a pure index computation with no floating-point-order-dependent
    accumulation, so results are exactly reproducible across NumPy
    versions and platforms — important for the determinism tests in
    `tests/dl/test_preprocessing.py`.
    """
    width, height = size
    src_h, src_w = gray.shape
    row_idx = (np.arange(height) * src_h // height).clip(0, src_h - 1)
    col_idx = (np.arange(width) * src_w // width).clip(0, src_w - 1)
    return gray[np.ix_(row_idx, col_idx)]


def preprocess_frame(frame: np.ndarray, size: Tuple[int, int]) -> np.ndarray:
    """
    Full preprocessing pipeline: validate -> grayscale -> resize ->
    normalize to [0, 1] -> flatten.

    Args:
        frame: A BGR, BGRA, or grayscale NumPy array.
        size: Target (width, height) to resize to (see
            `app.dl.config.DLConfig.image_size`).

    Returns:
        A 1-D float32 array of length `size[0] * size[1]`, values in
        [0.0, 1.0].

    Raises:
        DLError: if `frame` is None, not a NumPy array, has an
            unsupported shape/channel count, or is empty.
    """
    validated = _validate_frame(frame)
    gray = to_grayscale(validated)
    resized = resize_grayscale(gray, size)
    normalized = np.clip(resized / 255.0, 0.0, 1.0)
    return normalized.flatten().astype(np.float32)
