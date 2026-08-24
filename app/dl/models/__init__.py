"""
DL models package.

Holds the DL gesture contract (`gesture_types.py`: `GestureLabel`,
`GestureResult`, `DLError`) and the DL model definition itself
(`network.py`: `GestureMLP`, a small CPU-only NumPy MLP).

Public names are re-exported here so callers can write:

    from app.dl.models import GestureLabel, GestureResult, GestureMLP

This package has no dependency on Vision, Robot, ML, Navigation,
Decision, Guide, or app.main.
"""

from __future__ import annotations

from app.dl.models.gesture_types import DLError, GestureLabel, GestureResult
from app.dl.models.network import GestureMLP

__all__ = [
    "DLError",
    "GestureLabel",
    "GestureResult",
    "GestureMLP",
]
