"""
Gesture Mapper — maps gesture-level intents (`GestureIntent`) onto the
existing, unmodified `RobotCommandType` vocabulary.

Per the Robot Gestures phase rules, this module must NOT add, remove,
or rename any `RobotCommandType` member. A `GestureIntent` is only
"supported" here if an existing `RobotCommandType` member already
expresses the same physical action. Where no existing command type
safely corresponds to a gesture intent, the mapping is `None` and the
gesture is treated as currently unsupported rather than force-fit onto
a semantically mismatched existing command (see `PHASE_REPORT.md` for
the reasoning behind each unmapped gesture).

This module has no dependency on Vision, Decision, Guide, ML, DL,
Navigation, or app.main. It depends only on `app.robot.robot_commands`
(the existing Robot command vocabulary) and this phase's own
`gesture_definitions`.
"""

from __future__ import annotations

from typing import Dict, Optional

from app.robot.gesture_definitions import GestureError, GestureIntent
from app.robot.robot_commands import RobotCommandType

# The gesture -> existing RobotCommandType mapping.
#
# Only gestures with an unambiguous, already-existing RobotCommandType
# counterpart are mapped. Everything else maps to None and is reported
# as unsupported by `map_gesture_to_command` / `is_gesture_supported`
# rather than being silently attached to a mismatched existing command
# or a new command type invented for this phase.
GESTURE_TO_ROBOT_COMMAND: Dict[GestureIntent, Optional[RobotCommandType]] = {
    GestureIntent.WAVE: RobotCommandType.WAVE,
    GestureIntent.IDLE: RobotCommandType.IDLE,
    GestureIntent.POINT: None,
    GestureIntent.ACKNOWLEDGE: None,
    GestureIntent.THINKING: None,
    GestureIntent.ARRIVED: None,
}


def map_gesture_to_command(gesture: GestureIntent) -> Optional[RobotCommandType]:
    """
    Return the existing `RobotCommandType` that implements `gesture`,
    or `None` if no existing command type safely corresponds to it.

    Raises:
        GestureError: if `gesture` is not a `GestureIntent` member.
    """

    if not isinstance(gesture, GestureIntent):
        raise GestureError(
            f"map_gesture_to_command() requires a GestureIntent, "
            f"got {type(gesture)!r}"
        )
    return GESTURE_TO_ROBOT_COMMAND.get(gesture)


def is_gesture_supported(gesture: GestureIntent) -> bool:
    """Return True if `gesture` currently maps to an existing command."""

    return map_gesture_to_command(gesture) is not None


SUPPORTED_GESTURES = frozenset(
    gesture
    for gesture, command in GESTURE_TO_ROBOT_COMMAND.items()
    if command is not None
)

UNSUPPORTED_GESTURES = frozenset(
    gesture
    for gesture, command in GESTURE_TO_ROBOT_COMMAND.items()
    if command is None
)
