"""
DL gesture contract — the ONLY definitions of `GestureLabel` and
`GestureResult` in this project (mirrors the existing precedent set by
`DetectionResult` in `app.models.schemas`, `RobotExecutionResult` in
`app.robot.robot_controller`, and `GuideResponse` in
`app.guide.guide_service`: a producer's own result type lives in the
producing module rather than being forced into `app.models`).

This is the stable boundary a future integration layer consumes (see
`docs/dl.md`, "Integration boundary"). It intentionally reuses none of
`app.robot.gesture_definitions.GestureIntent` — that vocabulary
describes what the ROBOT should physically do next; `GestureLabel`
describes what the DL layer OBSERVED a human perform. They are related
but distinct concerns and a future integration/adapter layer, not this
module, owns translating one into the other (see docs/dl.md).

This module has no dependency on Vision, Robot, ML, Navigation,
Decision, Guide, or app.main. It depends only on the Python standard
library.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Mapping, Optional


class GestureLabel(Enum):
    """
    The gesture vocabulary the DL layer recognizes.

    This is the exact vocabulary already documented as the DL phase's
    plan in `app/dl/__init__.py` and `docs/architecture.md` prior to
    this implementation — pinned here as the single source of truth so
    it cannot silently drift. `UNKNOWN` is a first-class member, not an
    afterthought: it is the explicit "no confident gesture" state (see
    `GestureResult.unknown()` and docs/dl.md "Confidence semantics").
    """

    WAVE = "WAVE"
    STOP = "STOP"
    POINT = "POINT"
    UNKNOWN = "UNKNOWN"


class DLError(RuntimeError):
    """
    Raised for DL programmer/configuration errors: malformed input
    (wrong type, wrong shape, empty frame), a missing/malformed model
    artifact, or a required-but-unavailable trained model.

    Mirrors the existing project pattern (compare
    `app.robot.gesture_definitions.GestureError`,
    `app.config.ConfigurationError`): errors that indicate the caller
    or the deployment is misconfigured are raised, while ordinary,
    recoverable inference outcomes (e.g. a low-confidence frame) are
    reported as data via `GestureResult(gesture=GestureLabel.UNKNOWN,
    ...)` rather than raised. This keeps DL's failure-handling
    consistent with `RobotController`'s and the gesture layer's own
    fail-safe-by-default convention (see docs/dl.md "Error handling").
    """


@dataclass(frozen=True)
class GestureResult:
    """
    Canonical output of the DL layer for a single processed input.

    Attributes:
        gesture: The recognized gesture, or `GestureLabel.UNKNOWN` if
            no gesture could be confidently recognized.
        confidence: Softmax confidence of `gesture` in [0.0, 1.0].
            Always genuinely produced by the model — DL never invents
            or hardcodes this value (see docs/dl.md).
        scores: The full per-label probability distribution the model
            produced, for callers that want more than the argmax
            (e.g. a future integration layer applying its own
            threshold policy). Keys are `GestureLabel.value` strings
            (framework-independent) and values sum to ~1.0.
        timestamp: UTC time the result was produced.
        metadata: Small amount of additional, framework-independent
            context (e.g. {"reason": "low_confidence"},
            {"model_source": "fixture"}). Must never leak
            framework-specific tensors/arrays — see docs/dl.md.
    """

    gesture: GestureLabel
    confidence: float
    scores: Mapping[str, float]
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.gesture, GestureLabel):
            raise ValueError(
                f"GestureResult.gesture must be a GestureLabel, got "
                f"{type(self.gesture)!r}"
            )
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"GestureResult.confidence must be within [0.0, 1.0], "
                f"got {self.confidence}"
            )
        expected_keys = {member.value for member in GestureLabel}
        actual_keys = set(self.scores.keys())
        if actual_keys and actual_keys != expected_keys:
            raise ValueError(
                f"GestureResult.scores keys must exactly match "
                f"{sorted(expected_keys)} when non-empty, got "
                f"{sorted(actual_keys)}"
            )
        if actual_keys:
            total = sum(self.scores.values())
            if not (0.99 <= total <= 1.01):
                raise ValueError(
                    f"GestureResult.scores must sum to ~1.0, got {total}"
                )

    @staticmethod
    def unknown(
        reason: str,
        scores: Optional[Mapping[str, float]] = None,
        confidence: float = 0.0,
        timestamp: Optional[datetime] = None,
    ) -> "GestureResult":
        """
        Convenience constructor for an explicit "no confident gesture"
        result (mirrors `DetectionResult.empty()` in
        `app.models.schemas`).

        Args:
            reason: Short, human-readable reason recorded in
                `metadata["reason"]` (e.g. "low_confidence",
                "no_input_provided").
            scores: The model's full score distribution, if available
                (e.g. a below-threshold prediction). Omit entirely
                (leave as `{}`) when no distribution exists at all.
            confidence: The (low) confidence that triggered UNKNOWN, if
                applicable. Defaults to 0.0.
            timestamp: Defaults to now (UTC).
        """
        return GestureResult(
            gesture=GestureLabel.UNKNOWN,
            confidence=confidence,
            scores=dict(scores) if scores is not None else {},
            timestamp=timestamp or datetime.now(timezone.utc),
            metadata={"reason": reason},
        )
