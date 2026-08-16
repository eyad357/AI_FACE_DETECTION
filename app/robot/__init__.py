"""
Robot layer (Person 2 — Robotics / Robot Control).

Responsibility: answer "HOW should the physical action be performed?"
given a RobotCommand. Robot does NOT decide WHEN to act — that remains
Decision's / the future app.main orchestrator's responsibility.

This package MUST NOT import app.vision, app.decision, or app.guide. It
depends only on the Python standard library and app.utils.logger. See
docs/integration_contract.md for the full dependency rules.
"""

from app.robot.robot_commands import RobotCommand, RobotCommandType
from app.robot.robot_controller import (
    RobotBackend,
    RobotController,
    RobotError,
    RobotExecutionResult,
    SimulatedRobotBackend,
)

__all__ = [
    "RobotCommand",
    "RobotCommandType",
    "RobotController",
    "RobotBackend",
    "SimulatedRobotBackend",
    "RobotExecutionResult",
    "RobotError",
]
