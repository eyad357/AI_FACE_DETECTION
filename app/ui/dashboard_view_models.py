"""
View models for the Production Demo Dashboard.

Responsibility: define the plain, framework-independent data shapes
the dashboard renders. These are additive to (never a replacement of)
the existing Route Display view models in app.ui.view_models
(SystemStatus, RouteView, NavigationView, GuideContentView, ...),
which this module reuses rather than duplicates for anything
navigation/guide related.

None of these types hold business logic -- they are populated by
app.ui.dashboard_service.DashboardService from real application
objects returned by the app.ui.adapters.* modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids a hard numpy import here
    import numpy as np


class HealthState(Enum):
    """Per-subsystem health status shown in status cards / system health."""

    PASS = "PASS"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class SubsystemStatus:
    """
    A single subsystem's status, for the top status cards and the
    System Health panel.

    Attributes:
        name: Display name of the subsystem (e.g. "Vision").
        state: PASS / DEGRADED / UNAVAILABLE.
        detail: Short, honest human-readable explanation of the state
            (e.g. "No trained artifact -- using untrained fixture" or
            "Camera unavailable at index 0"). Never fabricated.
    """

    name: str
    state: HealthState
    detail: str = ""


@dataclass(frozen=True)
class PerceptionPanelView:
    """
    Display-ready state for the Camera / Perception panel.

    Attributes:
        camera_available: Whether the Camera device could be opened.
        detected: Whether the latest DetectionResult found a face.
            None when no detection has been attempted yet this
            session.
        face_count: Face count from the latest real DetectionResult.
        confidence: Confidence from the latest real DetectionResult,
            if the detector provides one.
        timestamp: When the latest real detection was produced.
        unavailable_reason: Honest explanation when camera_available
            is False (e.g. "No camera device detected in this
            environment").
        frame: The raw captured frame (BGR, as returned by
            app.vision.camera.Camera.read()), for display purposes
            only, when a frame was actually read this call. None when
            camera_available is False or no frame could be read.
            Optional/additive field -- existing callers that only use
            the fields above are unaffected.
    """

    camera_available: bool
    detected: Optional[bool] = None
    face_count: Optional[int] = None
    confidence: Optional[float] = None
    timestamp: Optional[datetime] = None
    unavailable_reason: Optional[str] = None
    frame: Optional["np.ndarray"] = None


@dataclass(frozen=True)
class InteractionPanelView:
    """
    Display-ready state for the Interaction panel, built from a real
    app.speech.response.ConversationResponse (and, when available, a
    real app.models.schemas.IntentResult from ML).
    """

    user_text: str
    spoken_text: str
    response_type: str
    language: str
    intent_label: Optional[str] = None
    intent_confidence: Optional[float] = None
    requires_clarification: bool = False
    destination: Optional[str] = None


@dataclass(frozen=True)
class RobotPanelView:
    """
    Display-ready state for the Robot panel, built from a real
    app.robot.robot_controller.RobotExecutionResult returned by
    app.integration.robot_adapter.RobotIntegrationAdapter.
    """

    backend_mode: str  # "SIMULATED" (this dashboard never drives real hardware)
    last_command: Optional[str] = None
    last_gesture_hint: Optional[str] = None
    last_success: Optional[bool] = None
    last_message: Optional[str] = None
    last_action_timestamp: Optional[datetime] = None


@dataclass(frozen=True)
class EventRecord:
    """
    A single row in the Event / Decision Timeline. Only ever created
    from a real action the dashboard actually performed during this
    session -- never backdated or fabricated.
    """

    timestamp: datetime
    source: str
    event: str
    detail: str = ""


@dataclass(frozen=True)
class DemoScenarioDescriptor:
    """
    One entry in the Demo Scenarios panel.

    Attributes:
        key: Stable identifier used to trigger the scenario.
        title: Display name.
        description: One-line explanation of what the scenario does.
        available: Whether current project capabilities can actually
            execute this scenario end-to-end.
        unavailable_reason: Honest explanation when available=False.
    """

    key: str
    title: str
    description: str
    available: bool
    unavailable_reason: Optional[str] = None


@dataclass
class DashboardSession:
    """
    Mutable, in-process session state for a single dashboard run.

    Holds only what actually happened during this session (event
    timeline, last panels) -- never pre-seeded with fake history.
    """

    session_id: str
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    events: List[EventRecord] = field(default_factory=list)

    def record(self, source: str, event: str, detail: str = "") -> EventRecord:
        record = EventRecord(
            timestamp=datetime.now(timezone.utc),
            source=source,
            event=event,
            detail=detail,
        )
        self.events.append(record)
        return record
