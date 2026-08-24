"""
DL dataset package.

- `fixture.py`: deterministic synthetic dataset generator, used only
  to exercise the training pipeline and produce the shipped demo
  artifact. Never a stand-in for real gesture-recognition accuracy.
- `loader.py`: the documented, explicit mechanism for loading a REAL
  gesture image dataset from disk once one exists (see docs/dl.md).

This package has no dependency on Vision, Robot, ML, Navigation,
Decision, Guide, or app.main. `loader.py` uses OpenCV only for image
file decoding.
"""

from __future__ import annotations

from app.dl.dataset.fixture import FIXTURE_LABEL_ORDER, generate_fixture_dataset
from app.dl.dataset.loader import DATASET_LABEL_ORDER, load_dataset_from_directory

__all__ = [
    "FIXTURE_LABEL_ORDER",
    "generate_fixture_dataset",
    "DATASET_LABEL_ORDER",
    "load_dataset_from_directory",
]
