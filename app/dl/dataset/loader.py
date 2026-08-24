"""
Loader for a REAL gesture image dataset, once one exists.

No real dataset ships with this project (see `fixture.py` for the
synthetic pipeline-testing stand-in, and docs/dl.md "Dataset format"
for the full explanation of why). This module is the explicit,
documented mechanism for plugging a real one in later, without any
other DL code changing.

Expected directory layout (one subdirectory per `GestureLabel`,
containing image files OpenCV can read — .png/.jpg/.jpeg/.bmp):

    <dataset_root>/
        WAVE/
            img001.png
            img002.jpg
            ...
        STOP/
            ...
        POINT/
            ...
        UNKNOWN/
            ...

Every image is run through the exact same
`app.dl.inference.preprocessing.preprocess_frame` pipeline used at
inference time, so a model trained on a real dataset loaded this way
is guaranteed to see input in the same distribution it will see in
production — the single most common source of a silent train/inference
mismatch.

This module MAY use OpenCV (already a project dependency, via
`requirements.txt`) purely for image-file *decoding* (reading a .png/
.jpg off disk into a NumPy array) — nothing else. It has no dependency
on Vision, Robot, ML, Navigation, Decision, Guide, or app.main; in
particular it does NOT import `app.vision.camera` or
`app.vision.face_detector`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple, Union

import numpy as np

from app.dl.inference.preprocessing import preprocess_frame
from app.dl.models.gesture_types import DLError, GestureLabel

_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp")

# Must match app.dl.inference.engine._LABEL_ORDER /
# app.dl.dataset.fixture.FIXTURE_LABEL_ORDER exactly.
DATASET_LABEL_ORDER: Tuple[GestureLabel, ...] = (
    GestureLabel.WAVE,
    GestureLabel.STOP,
    GestureLabel.POINT,
    GestureLabel.UNKNOWN,
)


def load_dataset_from_directory(
    dataset_root: Union[str, Path], image_size: Tuple[int, int]
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Load and preprocess a real gesture dataset from disk.

    Args:
        dataset_root: Path to the dataset root directory (see module
            docstring for the expected layout).
        image_size: (width, height) to resize every image to — pass
            `app.dl.config.DL_CONFIG.image_size` so the result is
            compatible with the shipped/trained `GestureMLP`.

    Returns:
        (X, y): X has shape (N, width*height), float32, in [0, 1]. y
        has shape (N,), int64 class indices into `DATASET_LABEL_ORDER`.

    Raises:
        DLError: if `dataset_root` does not exist, contains no
            recognized label subdirectories, or a label subdirectory
            contains no readable images.
    """
    # Imported lazily: this is the ONLY function in the DL package that
    # touches OpenCV, and only for image-file decoding, kept isolated
    # so the rest of DL (including all inference/training logic) never
    # depends on it.
    import cv2

    root = Path(dataset_root)
    if not root.is_dir():
        raise DLError(f"Dataset root does not exist or is not a directory: {root}")

    features = []
    labels = []
    for class_index, label in enumerate(DATASET_LABEL_ORDER):
        label_dir = root / label.value
        if not label_dir.is_dir():
            continue
        image_paths = sorted(
            p for p in label_dir.iterdir() if p.suffix.lower() in _IMAGE_EXTENSIONS
        )
        for image_path in image_paths:
            frame = cv2.imread(str(image_path))
            if frame is None:
                raise DLError(f"Failed to read image file: {image_path}")
            features.append(preprocess_frame(frame, image_size))
            labels.append(class_index)

    if not features:
        raise DLError(
            f"No images found under {root} (expected subdirectories named "
            f"{[label.value for label in DATASET_LABEL_ORDER]}, each "
            f"containing image files)"
        )

    return np.stack(features).astype(np.float32), np.array(labels, dtype=np.int64)
