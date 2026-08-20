"""
Robot Controller.

Responsibility: execute RobotCommands — i.e. answer "HOW should the
physical robot perform an action?" It does NOT decide WHEN an action
should occur; that belongs to Decision / the future app.main
orchestrator.

RobotController MUST NOT import app.vision, app.decision, or app.guide,
and MUST NOT inspect DetectionResult, DecisionEvent, ApplicationState,
or GuideResponse. It only ever receives a RobotCommand.

No physical robot SDK exists in this project. The default backend is a
deterministic, hardware-free simulation that records and logs each
command rather than pretending a physical action occurred — safe for
development, testing, and CI.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from app.robot.robot_commands import (
    SPEECH_COMMAND_TYPES,
    RobotCommand,
    RobotCommandType,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RobotError(RuntimeError):
    """
    Raised for Robot programmer/configuration errors (e.g. calling
    execute() with something that isn't a RobotCommand).

    Normal execution failures (empty speech text, a backend that fails)
    are NOT raised as exceptions — they are reported via a
    RobotExecutionResult with success=False, so callers can handle them
    deterministically without a try/except around every command.
    """


@dataclass(frozen=True)
class RobotExecutionResult:
    """
    Local result of executing a single RobotCommand.

    This is Robot's own result contract, not a shared cross-module
    model — no equivalent existed anywhere in the project, and this
    result never needs to cross a module boundary (Decision/Guide never
    consume it). This follows the same pattern already used for
    GuideResponse: a producing module's own output type, kept local
    rather than added to app/models/schemas.py.

    Attributes:
        command_type: Which command this result corresponds to.
        success: Whether the command was executed successfully.
        message: Human-readable outcome detail (never large speech
            content — just a short status message).
    """

    command_type: RobotCommandType
    success: bool
    message: str


class RobotBackend(ABC):
    """
    Minimal execution backend abstraction.

    Exists so RobotController never talks to hardware/SDK details
    directly, and so a real hardware backend can be swapped in later
    without changing RobotController's public API.

    To add a future hardware backend: subclass RobotBackend, implement
    execute(), and pass an instance to RobotController(backend=...).
    No change to RobotController, RobotCommand, RobotCommandType, or
    RobotExecutionResult is required to do this — those contracts are
    intentionally backend-independent. This class cannot be
    instantiated directly (it is an ABC); only concrete subclasses like
    SimulatedRobotBackend can be.
    """

    @abstractmethod
    def execute(self, command: RobotCommand) -> RobotExecutionResult:
        """Execute a single already-validated RobotCommand."""
        raise NotImplementedError


class SimulatedRobotBackend(RobotBackend):
    """
    Default, hardware-free backend.

    Records and logs each command deterministically rather than
    performing (or pretending to perform) a physical action. Requires no
    hardware, SDK, or network access — safe for development, testing,
    and CI.
    """

    def __init__(self) -> None:
        self._history: List[RobotCommand] = []

    @property
    def history(self) -> List[RobotCommand]:
        """Commands executed so far, in order (useful for tests)."""
        return list(self._history)

    def execute(self, command: RobotCommand) -> RobotExecutionResult:
        self._history.append(command)
        logger.info(
            "Simulated robot action executed: %s", command.command_type.value
        )
        return RobotExecutionResult(
            command_type=command.command_type,
            success=True,
            message=f"Simulated execution of {command.command_type.value}",
        )


class RobotController:
    """
    Executes RobotCommands via a pluggable backend.

    Usage:
        controller = RobotController()
        controller.greet()
        controller.speak("Welcome to the lab.")
        controller.execute(RobotCommand(RobotCommandType.WAVE))
    """

    def __init__(self, backend: Optional[RobotBackend] = None) -> None:
        self._backend: RobotBackend = backend if backend is not None else SimulatedRobotBackend()
        logger.info("Robot controller initialized")

    def execute(self, command: RobotCommand) -> RobotExecutionResult:
        """
        Execute a single RobotCommand.

        Args:
            command: The command to execute.

        Returns:
            A RobotExecutionResult describing the outcome. Never raises
            for normal execution failures (e.g. empty speech text, a
            backend failure) — those are reported as success=False with
            a clear message, so Robot fails safely.

        Raises:
            RobotError: For programmer errors — `command` is not a
                RobotCommand instance.
        """
        if not isinstance(command, RobotCommand):
            raise RobotError(
                f"execute() requires a RobotCommand, got {type(command)!r}"
            )

        logger.info("Robot command received: %s", command.command_type.value)

        if command.command_type in SPEECH_COMMAND_TYPES:
            if not command.text or not command.text.strip():
                logger.warning(
                    "Rejected %s command with empty speech text",
                    command.command_type.value,
                )
                return RobotExecutionResult(
                    command_type=command.command_type,
                    success=False,
                    message="Speech command requires non-empty text",
                )

        try:
            result = self._backend.execute(command)
        except Exception as exc:  # backend failure -> safe, reported result
            logger.error(
                "Robot backend failed executing %s: %s",
                command.command_type.value,
                exc,
            )
            return RobotExecutionResult(
                command_type=command.command_type,
                success=False,
                message=f"Backend execution failed: {exc}",
            )

        return result

    # ------------------------------------------------------------------
    # Convenience wrappers for the most common commands
    # ------------------------------------------------------------------

    def greet(self) -> RobotExecutionResult:
        return self.execute(RobotCommand(RobotCommandType.GREET))

    def wave(self) -> RobotExecutionResult:
        return self.execute(RobotCommand(RobotCommandType.WAVE))

    def speak(self, text: str) -> RobotExecutionResult:
        return self.execute(RobotCommand(RobotCommandType.SPEAK, text=text))

    def idle(self) -> RobotExecutionResult:
        return self.execute(RobotCommand(RobotCommandType.IDLE))

    def stop(self) -> RobotExecutionResult:
        return self.execute(RobotCommand(RobotCommandType.STOP))
