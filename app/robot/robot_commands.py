"""
Robot Commands — the stable public command vocabulary for the Robot
module.

This module defines WHAT action the robot should execute. It does NOT
decide WHEN an action should occur — that remains the responsibility of
Decision / the future app.main orchestrator (not implemented in this
phase).

The command vocabulary itself was documented conceptually back in
Phase 1 and is formalized here, for the first time, as an actual typed
Enum + command object. The vocabulary is unchanged from that original
documentation:

    GREET, WAVE, SPEAK, EXPLAIN_AI, EXPLAIN_ROBOTICS, EXPLAIN_TRAINING,
    EXPLAIN_LAB, IDLE, STOP

This module has no dependency on Vision, Decision, or Guide.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class RobotCommandType(Enum):
    """
    The stable set of physical actions the Robot Controller can execute.

    This is the single canonical robot command vocabulary for the
    project — do not redefine it elsewhere.
    """

    GREET = "GREET"
    WAVE = "WAVE"
    SPEAK = "SPEAK"
    EXPLAIN_AI = "EXPLAIN_AI"
    EXPLAIN_ROBOTICS = "EXPLAIN_ROBOTICS"
    EXPLAIN_TRAINING = "EXPLAIN_TRAINING"
    EXPLAIN_LAB = "EXPLAIN_LAB"
    IDLE = "IDLE"
    STOP = "STOP"


# Commands that carry spoken text. EXPLAIN_* commands are paired with
# text a future orchestrator already obtained from Guide
# (GuideResponse.spoken_text) — Robot itself holds no educational
# content and never decides what to say, only how to deliver it.
SPEECH_COMMAND_TYPES = frozenset(
    {
        RobotCommandType.SPEAK,
        RobotCommandType.EXPLAIN_AI,
        RobotCommandType.EXPLAIN_ROBOTICS,
        RobotCommandType.EXPLAIN_TRAINING,
        RobotCommandType.EXPLAIN_LAB,
    }
)


@dataclass(frozen=True)
class RobotCommand:
    """
    A single instruction for the Robot Controller to execute.

    Attributes:
        command_type: WHAT action to perform (see RobotCommandType).
        text: Spoken text. Required (non-empty) for SPEAK/EXPLAIN_*
            commands; ignored otherwise. Robot only delivers this text —
            it never originates or selects it; that is Guide's
            responsibility, mediated by the future orchestrator.
        metadata: Optional small amount of extra execution-relevant
            information. Must never carry Vision/Decision/Guide
            implementation details.
    """

    command_type: RobotCommandType
    text: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
