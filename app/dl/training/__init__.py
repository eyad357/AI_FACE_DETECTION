"""
DL training package.

- `trainer.py`: `GestureTrainer`, manual backprop/SGD training for
  `GestureMLP`.
- `train_fixture_model.py`: reproducible entry point
  (`python -m app.dl.training.train_fixture_model`) that trains on the
  synthetic fixture dataset and saves the shipped demo artifact.

This package has no dependency on Vision, Robot, ML, Navigation,
Decision, Guide, or app.main.
"""

from __future__ import annotations

from app.dl.training.trainer import GestureTrainer, TrainingResult

__all__ = ["GestureTrainer", "TrainingResult"]
