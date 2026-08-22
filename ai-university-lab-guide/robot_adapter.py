"""
Robot Integration Adapter.

Responsibility: translate high-level, application-level Robot-facing
actions (e.g. "greet the visitor", "say this", "explain this topic")
into calls against the existing, unmodified `app.robot` public API —
i.e. answer "which existing Robot capability does this application
action correspond to, and how do I invoke it?"

`RobotIntegrationAdapter` is a thin translation boundary. It is NOT an
orchestrator, decision engine, intent classifier, navigation engine,
Guide service, application-wide state manager, or a second Robot
controller. It never decides *when* an action should occur, *what* the
user wants, or *what* to say — it only takes an already-decided,
already-worded request and executes it through the existing
`RobotController`.

The adapter never talks to a `RobotBackend` directly, never
constructs its own backend, and never bypasses `RobotController`: it
wraps an existing `RobotController` instance (by composition) and
delegates every action to that controller's existing public methods
(`greet()`, `wave()`, `speak()`, `idle()`, `stop()`) or, for the four
`EXPLAIN_*` topics (which have no existing convenience wrapper on
`RobotController` itself), to the controller's existing `execute()`
method with an existing `RobotCommand`/`RobotCommandType`. No new
Robot command vocabulary, result type, or backend abstraction is
introduced by this module.

This module MUST NOT import app.vision, app.ml, or app.dl, and avoids
importing app.decision, app.guide, app.navigation, and app.main. It
depends only on the existing `app.robot` public API and
`app.utils.logger` (the same logging dependency the existing Robot
module already uses).
"""

from __future__ import annotations

from typing import Optional

from app.robot import (
    RobotCommand,
    RobotCommandType,
    RobotController,
    RobotExecutionResult,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AdapterError(RuntimeError):
    """
    Raised for adapter-level programmer/configuration errors (e.g.
    passing a non-string, non-None value where spoken text is
    expected).

    Normal execution outcomes — a Robot command that reports
    `success=False` (empty speech text, a backend failure) — are NOT
    raised as exceptions here either; the adapter simply returns
    whatever `RobotExecutionResult` the existing `RobotController`
    already produces, mirroring `RobotController.execute()`'s own
    fail-safe behavior. `AdapterError` is reserved for input that is
    invalid at the adapter boundary itself, before any existing Robot
    contract is even involved.
    """


# The four EXPLAIN_* topics are existing RobotCommandType members with
# no existing RobotController convenience wrapper (RobotController only
# wraps GREET/WAVE/SPEAK/IDLE/STOP) -- callers must otherwise build a
# RobotCommand and call execute() directly. This adapter provides one
# named, high-level method per existing topic instead, so callers never
# need to import RobotCommand/RobotCommandType themselves.
_EXPLAIN_COMMAND_TYPES = frozenset(
    {
        RobotCommandType.EXPLAIN_AI,
        RobotCommandType.EXPLAIN_ROBOTICS,
        RobotCommandType.EXPLAIN_TRAINING,
        RobotCommandType.EXPLAIN_LAB,
    }
)


def _validate_optional_text(value: object, *, param_name: str) -> None:
    """
    Validate that `value` is either `None` or a `str`.

    This is deliberately the *only* text validation the adapter
    performs. Content-level validation (e.g. rejecting empty/
    whitespace-only speech text) is already handled by the existing
    `RobotController.execute()` — which reports it as a normal,
    non-raising `RobotExecutionResult(success=False, ...)` — and is
    intentionally NOT duplicated here, to avoid creating a second,
    possibly-divergent copy of that existing behavior.

    Raises:
        AdapterError: if `value` is neither `None` nor a `str`.
    """

    if value is not None and not isinstance(value, str):
        raise AdapterError(
            f"{param_name} must be a string or None, got {type(value)!r}"
        )


class RobotIntegrationAdapter:
    """
    Translates high-level Robot-facing application actions into calls
    against the existing `RobotController` public API.

    Usage:
        adapter = RobotIntegrationAdapter()
        adapter.execute_greeting()
        adapter.speak("Welcome to the lab.")
        adapter.explain_ai("Here is what we do in AI research...")
        adapter.idle()
        adapter.stop()

    A caller may also supply an existing `RobotController` instance
    (e.g. one already configured with a particular `RobotBackend`, or
    already shared with another component) so the adapter participates
    in whatever Robot execution boundary the caller has already set
    up, rather than creating a disconnected one of its own.
    """

    def __init__(self, robot_controller: Optional[RobotController] = None) -> None:
        self._robot_controller: RobotController = (
            robot_controller if robot_controller is not None else RobotController()
        )
        logger.info("Robot integration adapter initialized")

    # ------------------------------------------------------------------
    # Supported high-level actions -- one per existing RobotCommandType.
    # ------------------------------------------------------------------

    def execute_greeting(self) -> RobotExecutionResult:
        """Greet the visitor, via the existing `RobotController.greet()`."""

        logger.info("Adapter: translating greeting request")
        return self._robot_controller.greet()

    def wave(self) -> RobotExecutionResult:
        """Wave, via the existing `RobotController.wave()`."""

        logger.info("Adapter: translating wave request")
        return self._robot_controller.wave()

    def speak(self, text: str) -> RobotExecutionResult:
        """
        Speak `text`, via the existing `RobotController.speak()`.

        Raises:
            AdapterError: if `text` is neither a `str` nor `None`.
        """

        _validate_optional_text(text, param_name="text")
        logger.info("Adapter: translating speech request")
        return self._robot_controller.speak(text)

    def idle(self) -> RobotExecutionResult:
        """Go idle, via the existing `RobotController.idle()`."""

        logger.info("Adapter: translating idle request")
        return self._robot_controller.idle()

    def stop(self) -> RobotExecutionResult:
        """Stop, via the existing `RobotController.stop()`."""

        logger.info("Adapter: translating stop request")
        return self._robot_controller.stop()

    def explain_ai(self, text: str) -> RobotExecutionResult:
        """Explain the AI topic, via the existing EXPLAIN_AI command."""

        return self._explain(RobotCommandType.EXPLAIN_AI, text)

    def explain_robotics(self, text: str) -> RobotExecutionResult:
        """Explain the Robotics topic, via the existing EXPLAIN_ROBOTICS command."""

        return self._explain(RobotCommandType.EXPLAIN_ROBOTICS, text)

    def explain_training(self, text: str) -> RobotExecutionResult:
        """Explain the Training topic, via the existing EXPLAIN_TRAINING command."""

        return self._explain(RobotCommandType.EXPLAIN_TRAINING, text)

    def explain_lab(self, text: str) -> RobotExecutionResult:
        """Explain the Lab topic, via the existing EXPLAIN_LAB command."""

        return self._explain(RobotCommandType.EXPLAIN_LAB, text)

    def _explain(
        self, command_type: RobotCommandType, text: str
    ) -> RobotExecutionResult:
        """
        Shared translation path for the four existing EXPLAIN_* topics.

        Raises:
            AdapterError: if `text` is neither a `str` nor `None`, or
                if `command_type` is not one of the four existing
                EXPLAIN_* members (a programmer error internal to this
                adapter, not something a caller of the four public
                `explain_*` methods above can trigger).
        """

        if command_type not in _EXPLAIN_COMMAND_TYPES:
            raise AdapterError(
                f"_explain() requires an EXPLAIN_* RobotCommandType, "
                f"got {command_type!r}"
            )
        _validate_optional_text(text, param_name="text")

        logger.info(
            "Adapter: translating explain request for %s", command_type.value
        )
        command = RobotCommand(command_type=command_type, text=text)
        return self._robot_controller.execute(command)
