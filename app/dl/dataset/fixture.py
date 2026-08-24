"""
Deterministic synthetic fixture dataset for the DL gesture pipeline.

No real gesture dataset ships with this project (see docs/dl.md
"Dataset format" for how to plug in a real one). Rather than fake
inference or fabricate accuracy claims, this module generates a small,
purely-synthetic, seeded dataset of simple geometric patterns — one
distinguishable pattern per `GestureLabel` — that the training pipeline
(`app.dl.training.trainer`) can genuinely learn from via real gradient
descent. This exists ONLY to:

1. exercise the training pipeline end-to-end in tests, deterministically
   and without any hardware/network/real dataset dependency;
2. produce the small demo artifact shipped at
   `app/dl/artifacts/gesture_mlp_fixture.npz`, which is explicitly
   labeled a "fixture-trained" model everywhere it is surfaced
   (`GestureRecognitionService`, docs/dl.md, PHASE_REPORT.md) and is
   NEVER described as accurate on real human gestures.

This module has no dependency on Vision, Robot, ML, Navigation,
Decision, Guide, or app.main.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np

from app.dl.models.gesture_types import GestureLabel

# Canonical label ordering for the fixture dataset's integer labels.
# Must match app.dl.inference.engine._LABEL_ORDER exactly, since the
# trained artifact's output index i is meaningless without it.
FIXTURE_LABEL_ORDER: Tuple[GestureLabel, ...] = (
    GestureLabel.WAVE,
    GestureLabel.STOP,
    GestureLabel.POINT,
    GestureLabel.UNKNOWN,
)


def _pattern_for_label(
    label: GestureLabel, size: Tuple[int, int]
) -> np.ndarray:
    """
    A deterministic (noise-free) base grayscale pattern, in [0, 255],
    for one gesture label. Patterns are simple, mutually distinguishable
    geometric shapes — NOT real gesture imagery — chosen only so a tiny
    MLP has something genuinely learnable to separate.
    """
    width, height = size
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    cx, cy = (width - 1) / 2.0, (height - 1) / 2.0

    if label is GestureLabel.WAVE:
        # Bright vertical band on the upper-right (an open hand raised
        # to one side).
        pattern = np.where((xx > width * 0.55) & (yy < height * 0.6), 220.0, 30.0)
    elif label is GestureLabel.STOP:
        # Bright filled disc in the center (a flat palm held up).
        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        pattern = np.where(dist < min(width, height) * 0.3, 220.0, 30.0)
    elif label is GestureLabel.POINT:
        # Bright diagonal band (an extended arm/finger).
        pattern = np.where(np.abs((xx - yy * (width / height))) < width * 0.12, 220.0, 30.0)
    elif label is GestureLabel.UNKNOWN:
        # Flat mid-gray field: deliberately featureless, representing
        # "no clear gesture" (e.g. an empty or ambiguous frame).
        pattern = np.full((height, width), 110.0, dtype=np.float32)
    else:  # pragma: no cover - exhaustive over GestureLabel
        raise ValueError(f"No fixture pattern defined for {label!r}")

    return pattern.astype(np.float32)


def generate_fixture_dataset(
    size: Tuple[int, int],
    samples_per_class: int = 40,
    noise_std: float = 25.0,
    seed: int = 0,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generate a deterministic synthetic dataset.

    Args:
        size: (width, height) of each generated grayscale image —
            should match `DLConfig.image_size` so the trained artifact
            is compatible with `InferenceEngine`.
        samples_per_class: How many noisy samples to generate per
            `GestureLabel`.
        noise_std: Standard deviation of the per-pixel Gaussian noise
            added to each base pattern (keeps the task non-trivial
            instead of a lookup table).
        seed: Random seed. The SAME seed always produces the EXACT
            same dataset (bit-identical), which is what makes the
            shipped fixture artifact's training reproducible.

    Returns:
        (X, y): X has shape (N, width*height), float32, values in
        [0, 1]. y has shape (N,), int64 class indices into
        `FIXTURE_LABEL_ORDER`.
    """
    if samples_per_class <= 0:
        raise ValueError(f"samples_per_class must be > 0, got {samples_per_class}")
    if noise_std < 0:
        raise ValueError(f"noise_std must be >= 0, got {noise_std}")

    width, height = size
    rng = np.random.default_rng(seed)

    features = []
    labels = []
    for class_index, label in enumerate(FIXTURE_LABEL_ORDER):
        base = _pattern_for_label(label, size)
        for _ in range(samples_per_class):
            noise = rng.normal(0.0, noise_std, size=(height, width)).astype(np.float32)
            noisy = np.clip(base + noise, 0.0, 255.0)
            features.append((noisy / 255.0).flatten())
            labels.append(class_index)

    X = np.stack(features).astype(np.float32)
    y = np.array(labels, dtype=np.int64)

    # Deterministic shuffle so classes are interleaved (helps SGD
    # convergence) but reproducibility is preserved (same seed -> same
    # permutation).
    permutation = rng.permutation(len(y))
    return X[permutation], y[permutation]
