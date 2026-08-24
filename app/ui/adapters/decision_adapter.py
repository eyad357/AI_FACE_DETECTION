"""
Decision adapter for the dashboard.

Wraps app.decision.state_manager.StateManager and re-exposes
app.decision.event_manager.ApplicationState / DecisionEvent /
GuideTopic (imported, never redefined) for the dashboard to render.
"""

from __future__ import annotations

from typing import List, Optional

from app.decision.event_manager import ApplicationState, DecisionEvent, GuideTopic
from app.decision.state_manager import StateManager
from app.models.schemas import DetectionResult
from app.ui.dashboard_view_models import HealthState, SubsystemStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DecisionAdapter:
    """Dashboard-facing wrapper around the real Decision state machine."""

    def __init__(self) -> None:
        self._manager: Optional[StateManager] = None
        self._init_error: Optional[str] = None
        try:
            self._manager = StateManager()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Decision unavailable: %s", exc)
            self._init_error = str(exc)

    def status(self) -> SubsystemStatus:
        if self._manager is None:
            return SubsystemStatus(
                name="Decision",
                state=HealthState.UNAVAILABLE,
                detail=self._init_error or "Decision state manager failed to initialize",
            )
        return SubsystemStatus(name="Decision", state=HealthState.PASS, detail="State manager ready")

    @property
    def state(self) -> Optional[ApplicationState]:
        return self._manager.state if self._manager is not None else None

    def process(self, detection_result: Optional[DetectionResult]) -> List[DecisionEvent]:
        """Feed a real DetectionResult into the state machine."""
        if self._manager is None:
            return []
        return self._manager.process(detection_result)

    def complete_greeting(self) -> List[DecisionEvent]:
        if self._manager is None:
            return []
        return self._manager.complete_greeting()

    def select_topic(self, topic: GuideTopic) -> List[DecisionEvent]:
        if self._manager is None:
            return []
        return self._manager.select_topic(topic)

    def complete_session(self) -> List[DecisionEvent]:
        if self._manager is None:
            return []
        return self._manager.complete_session()

    def reset(self) -> None:
        if self._manager is not None:
            self._manager.reset()
