"""
DL inference package.

- `preprocessing.py`: deterministic, dependency-light frame ->
  feature-vector conversion.
- `engine.py`: `InferenceEngine`, wiring preprocessing + `GestureMLP`
  into typed `GestureResult`s with confidence-threshold policy.

Consumed by `app.dl.service.GestureRecognitionService`, the module's
public API. This package has no dependency on Vision, Robot, ML,
Navigation, Decision, Guide, or app.main.
"""

from __future__ import annotations

from app.dl.inference.engine import InferenceEngine
from app.dl.inference.preprocessing import preprocess_frame

__all__ = ["InferenceEngine", "preprocess_frame"]
