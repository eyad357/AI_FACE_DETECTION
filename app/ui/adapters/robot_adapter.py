"""
Robot panel adapter for the dashboard.

Wraps the existing app.integration.robot_adapter.RobotIntegrationAdapter
-- itself a thin translation boundary over app.robot.RobotController.
This module never talks to app.robot.RobotBackend directly, never
constructs a second Robot controller, and never introduces a new
command vocabulary. The dashboard always runs against
SimulatedRobotBackend (app.robot.SimulatedRobotBackend) so it is
demonstrable without physical hardware, per the project's existing
simulation capability -- it never claims a physical connection that
does not exist.
"""

from __future__ import annotations

from typing import Optional

from app.integration import AdapterError, RobotIntegrationAdapter
from app.robot import RobotController, RobotExecutionResult, SimulatedRobotBackend
from app.ui.dashboard_view_models import HealthState, RobotPanelView, SubsystemStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)

_SAFE_EXPLAIN_ACTIONS = {
    "EXPLAIN_AI": "explain_ai",
    "EXPLAIN_ROBOTICS": "explain_robotics",
    "EXPLAIN_TRAINING": "explain_training",
    "EXPLAIN_LAB": "explain_lab",
}


class DashboardRobotAdapter:
    """
    Dashboard-facing wrapper around the real Robot Integration Adapter.

    Only exposes the actions the existing RobotIntegrationAdapter
    public API already supports: greet, wave, speak, explain_ai,
    explain_robotics, explain_training, explain_lab, idle, stop.
    """

    def __init__(self) -> None:
        self._adapter: Optional[RobotIntegrationAdapter] = None
        self._init_error: Optional[str] = None
        try:
            controller = RobotController(backend=SimulatedRobotBackend())
            self._adapter = RobotIntegrationAdapter(robot_controller=controller)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Robot integration unavailable: %s", exc)
            self._init_error = str(exc)

    def status(self) -> SubsystemStatus:
        if self._adapter is None:
            return SubsystemStatus(
                name="Robot",
                state=HealthState.UNAVAILABLE,
                detail=self._init_error or "Robot Integration Adapter failed to initialize",
            )
        return SubsystemStatus(
            name="Robot",
            state=HealthState.PASS,
            detail="Simulated backend connected (no physical hardware required)",
        )

    def integration_status(self) -> SubsystemStatus:
        """Separate status card for the Integration boundary itself."""
        if self._adapter is None:
            return SubsystemStatus(
                name="Integration",
                state=HealthState.UNAVAILABLE,
                detail=self._init_error or "Robot Integration Adapter unavailable",
            )
        return SubsystemStatus(name="Integration", state=HealthState.PASS, detail="Adapter ready")

    def _run(self, label: str, action) -> RobotPanelView:
        if self._adapter is None:
            return RobotPanelView(
                backend_mode="UNAVAILABLE",
                last_command=label,
                last_success=False,
                last_message=self._init_error or "Robot Integration Adapter unavailable",
            )
        try:
            result: RobotExecutionResult = action()
        except AdapterError as exc:
            return RobotPanelView(
                backend_mode="SIMULATED",
                last_command=label,
                last_success=False,
                last_message=str(exc),
            )
        return RobotPanelView(
            backend_mode="SIMULATED",
            last_command=result.command_type.value,
            last_success=result.success,
            last_message=result.message,
        )

    def greet(self) -> RobotPanelView:
        return self._run("GREET", lambda: self._adapter.execute_greeting())

    def wave(self) -> RobotPanelView:
        return self._run("WAVE", lambda: self._adapter.wave())

    def speak(self, text: str) -> RobotPanelView:
        return self._run("SPEAK", lambda: self._adapter.speak(text))

    def idle(self) -> RobotPanelView:
        return self._run("IDLE", lambda: self._adapter.idle())

    def stop(self) -> RobotPanelView:
        return self._run("STOP", lambda: self._adapter.stop())

    def explain(self, topic_key: str, text: str) -> RobotPanelView:
        """
        topic_key: one of "EXPLAIN_AI", "EXPLAIN_ROBOTICS",
        "EXPLAIN_TRAINING", "EXPLAIN_LAB" -- the existing
        RobotIntegrationAdapter method names, never a new vocabulary.
        """
        method_name = _SAFE_EXPLAIN_ACTIONS.get(topic_key)
        if method_name is None or self._adapter is None:
            return RobotPanelView(
                backend_mode="SIMULATED" if self._adapter else "UNAVAILABLE",
                last_command=topic_key,
                last_success=False,
                last_message=f"Unsupported explain topic: {topic_key}",
            )
        method = getattr(self._adapter, method_name)
        return self._run(topic_key, lambda: method(text))
