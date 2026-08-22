"""
Gesture Definitions — the gesture-level vocabulary for the Robot
Gestures phase.

This module defines gesture *intents*: higher-level, human-meaningful
labels (e.g. "wave at the visitor", "go idle") that a caller can
request without knowing which concrete `RobotCommandType` (if any)
currently implements them.

Gesture intents are a NEW, additive, gesture-layer-only vocabulary.
They are intentionally kept separate from `app.robot.robot_commands.
RobotCommandType` — the existing, stable, canonical Robot command
vocabulary — and are never merged into it. This module does not add,
remove, or rename any `RobotCommandType` member.

This module has no dependency on Vision, Decision, Guide, ML, DL,
Navigation, or app.main. It depends only on the Python standard
library.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class GestureIntent(Enum):
    """
    The set of gesture-level intents the gesture layer understands.

    These are intentionally distinct from `RobotCommandType`. Not every
    `GestureIntent` currently has a corresponding existing Robot
    capability to execute it against — see `gesture_mapper.py` for the
    (partial) mapping and `PHASE_REPORT.md` for the gestures that
    currently have no safe mapping and are therefore unsupported.
    """

    WAVE = "WAVE"
    POINT = "POINT"
    ACKNOWLEDGE = "ACKNOWLEDGE"
    THINKING = "THINKING"
    ARRIVED = "ARRIVED"
    IDLE = "IDLE"


class GestureError(RuntimeError):
    """
    Raised for gesture programmer/configuration errors (e.g. calling
    the gesture layer with something that isn't a `GestureRequest`, or
    a `GestureRequest` whose `gesture` field isn't a `GestureIntent`).

    Normal execution outcomes (an unsupported gesture, a failed
    downstream Robot execution) are NOT raised as exceptions — they are
    reported via a `GestureExecutionResult` with `success=False`,
    mirroring the existing `RobotController` pattern of failing safely
    rather than raising for expected, recoverable outcomes.
    """


@dataclass(frozen=True)
class GestureRequest:
    """
    A single request to perform a gesture.

    Attributes:
        gesture: WHICH gesture-level intent to perform (see
            `GestureIntent`).
        text: Optional spoken text to carry through to the underlying
            `RobotCommand`, for gestures that map to a Robot command
            capable of speech (e.g. a future ACKNOWLEDGE mapping onto a
            speech-capable command). Ignored for gestures that map to a
            non-speech command, exactly like `RobotCommand.text`.
        metadata: Optional small amount of extra execution-relevant
            information, forwarded as-is to the underlying
            `RobotCommand.metadata`. Must never carry Vision/Decision/
            Guide/ML/DL/Navigation implementation details.
    """

    gesture: GestureIntent
    text: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def validate_gesture_request(request: Any) -> None:
    """
    Validate that `request` is a well-formed `GestureRequest`.

    Raises:
        GestureError: if `request` is not a `GestureRequest` instance,
            or its `gesture` field is not a `GestureIntent` member.
    """

    if not isinstance(request, GestureRequest):
        raise GestureError(
            f"Expected a GestureRequest, got {type(request)!r}"
        )
    if not isinstance(request.gesture, GestureIntent):
        raise GestureError(
            f"GestureRequest.gesture must be a GestureIntent, "
            f"got {type(request.gesture)!r}"
        )
