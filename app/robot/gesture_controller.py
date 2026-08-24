"""
Gesture Controller.

Responsibility: turn a validated `GestureRequest` into an existing
`RobotCommand` and dispatch it through the existing, unmodified
`RobotController` — i.e. answer "how should a gesture-level intent be
carried out using capabilities the Robot module already has?"

`GestureController` is NOT a second, independent Robot controller. It
never talks to a `RobotBackend` directly, never bypasses
`RobotController`, and never invents hardware behavior of its own: it
wraps an existing `RobotController` instance (by composition) and
delegates all actual execution to `RobotController.execute()`.

`GestureController` MUST NOT import app.vision, app.ml, app.dl,
app.navigation, app.decision, or app.main. It depends only on this
phase's own gesture modules, the existing `app.robot` public API, and
`app.utils.logger` (the same logging dependency the existing Robot
module already uses).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from app.robot.gesture_definitions import (
    GestureError,
    GestureIntent,
    GestureRequest,
    validate_gesture_request,
)
from app.robot.gesture_mapper import map_gesture_to_command
from app.robot.robot_commands import RobotCommand
from app.robot.robot_controller import RobotController, RobotExecutionResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class GestureExecutionResult:
    """
    Local result of executing a single `GestureRequest`.

    This is the gesture layer's own result contract, kept local rather
    than added to `app/models/schemas.py` or to Robot's existing
    `RobotExecutionResult` — mirroring the precedent already set by
    `RobotExecutionResult` itself (a producing module's own output
    type that never needs to cross a module boundary).

    Attributes:
        gesture: Which gesture intent this result corresponds to.
        success: Whether the gesture was executed successfully. False
            both for gestures that currently have no existing Robot
            capability to map onto, and for gestures whose underlying
            `RobotCommand` execution failed.
        message: Human-readable outcome detail.
        robot_result: The underlying `RobotExecutionResult`, when the
            gesture was mapped to an existing command and dispatched
            through `RobotController`. `None` for gestures that have
            no existing mapping (dispatch never happened).
    """

    gesture: GestureIntent
    success: bool
    message: str
    robot_result: Optional[RobotExecutionResult] = None


class GestureController:
    """
    Executes gesture-level intents via the existing `RobotController`.

    Usage:
        controller = GestureController()
        controller.execute_gesture(GestureRequest(GestureIntent.WAVE))
        controller.execute_sequence([
            GestureRequest(GestureIntent.WAVE),
            GestureRequest(GestureIntent.IDLE),
        ])

    A caller may also supply an existing `RobotController` instance
    (e.g. one already configured with a particular `RobotBackend`) so
    the gesture layer participates in whatever Robot execution
    boundary the caller has already set up, rather than creating a
    disconnected one of its own.
    """

    def __init__(self, robot_controller: Optional[RobotController] = None) -> None:
        self._robot_controller: RobotController = (
            robot_controller if robot_controller is not None else RobotController()
        )
        logger.info("Gesture controller initialized")

    def execute_gesture(self, request: GestureRequest) -> GestureExecutionResult:
        """
        Execute a single `GestureRequest`.

        Args:
            request: The gesture request to execute.

        Returns:
            A `GestureExecutionResult` describing the outcome. Never
            raises for normal execution outcomes (an unsupported
            gesture, a failed underlying `RobotCommand` execution) —
            those are reported as `success=False` with a clear
            message, mirroring `RobotController.execute()`'s
            fail-safe behavior.

        Raises:
            GestureError: For programmer errors — `request` is not a
                `GestureRequest`, or its `gesture` field is not a
                `GestureIntent`.
        """

        validate_gesture_request(request)

        logger.info("Gesture request received: %s", request.gesture.value)

        command_type = map_gesture_to_command(request.gesture)
        if command_type is None:
            message = (
                f"Gesture {request.gesture.value} has no corresponding "
                "existing RobotCommandType and is not currently supported."
            )
            logger.warning(
                "Rejected unsupported gesture: %s", request.gesture.value
            )
            return GestureExecutionResult(
                gesture=request.gesture,
                success=False,
                message=message,
                robot_result=None,
            )

        command = RobotCommand(
            command_type=command_type,
            text=request.text,
            metadata=request.metadata,
        )
        robot_result = self._robot_controller.execute(command)

        return GestureExecutionResult(
            gesture=request.gesture,
            success=robot_result.success,
            message=robot_result.message,
            robot_result=robot_result,
        )

    def execute_sequence(
        self, requests: List[GestureRequest]
    ) -> List[GestureExecutionResult]:
        """
        Execute a sequence of `GestureRequest`s in order.

        Every request in the sequence is attempted, in order, even if
        an earlier one is unsupported or fails — mirroring
        `RobotController`'s own fail-safe-per-command behavior rather
        than aborting the whole sequence. Callers that need
        stop-on-failure semantics can inspect each
        `GestureExecutionResult.success` themselves.

        Args:
            requests: The gesture requests to execute, in order.

        Returns:
            A list of `GestureExecutionResult`, one per request, in
            the same order as `requests`.

        Raises:
            GestureError: For programmer errors, propagated from
                `execute_gesture()` — e.g. an element of `requests`
                that is not a `GestureRequest`.
        """

        return [self.execute_gesture(request) for request in requests]
