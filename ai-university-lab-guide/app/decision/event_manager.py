"""
Application-level event and state vocabulary for the Decision layer.

This module defines *what the application can be doing* (ApplicationState)
and *what the application decides should happen next* (DecisionEvent /
DecisionEventType). These are intentionally NOT Robot commands — they are
intents that a future orchestration layer (app.main) will translate into
Robot behavior, Guide content, and UI updates.

This module has no dependency on app.vision or app.robot. It depends only
on the Python standard library and app.models (for type hints referenced
in docstrings/consumers), keeping it safe to import from anywhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class ApplicationState(Enum):
    """
    Application-level states for the guide interaction session.

    These are NOT hardware states — there is no ROBOT_WAVING or
    ROBOT_SPEAKING here. Robot implementation state belongs to app.robot.
    """

    WAITING = "WAITING"
    GREETING = "GREETING"
    GUIDE_MENU = "GUIDE_MENU"
    EXPLAINING = "EXPLAINING"
    COOLDOWN = "COOLDOWN"
    ERROR = "ERROR"


class DecisionEventType(Enum):
    """Application-level events/intents produced by the Decision layer."""

    NO_VISITOR = "NO_VISITOR"
    VISITOR_DETECTED = "VISITOR_DETECTED"
    MULTIPLE_VISITORS = "MULTIPLE_VISITORS"
    GREETING_REQUIRED = "GREETING_REQUIRED"
    GUIDE_MENU_REQUIRED = "GUIDE_MENU_REQUIRED"
    TOPIC_SELECTED = "TOPIC_SELECTED"
    EXPLANATION_REQUIRED = "EXPLANATION_REQUIRED"
    SESSION_COMPLETED = "SESSION_COMPLETED"
    COOLDOWN_STARTED = "COOLDOWN_STARTED"
    RETURN_TO_WAITING = "RETURN_TO_WAITING"
    ERROR = "ERROR"


class GuideTopic(Enum):
    """
    Typed guide topics a visitor may select in GUIDE_MENU.

    Decision only tracks WHICH topic was selected — it does not contain
    the actual educational content. Content belongs to app.guide.content
    (not implemented in this phase).
    """

    AI_PROJECTS = "AI_PROJECTS"
    ROBOTICS = "ROBOTICS"
    TRAINING = "TRAINING"
    LAB_INFORMATION = "LAB_INFORMATION"


@dataclass(frozen=True)
class DecisionEvent:
    """
    A single application-level event/intent produced by the Decision
    layer, meant for the future orchestration layer (app.main) to
    consume.

    Attributes:
        event_type: What kind of event this is.
        timestamp: When the event was produced.
        metadata: Optional small amount of extra, orchestration-relevant
            information (e.g. face_count, selected topic). Must never
            contain Robot-specific instructions.
    """

    event_type: DecisionEventType
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


def create_event(
    event_type: DecisionEventType,
    timestamp: datetime,
    metadata: Optional[Dict[str, Any]] = None,
) -> DecisionEvent:
    """Convenience factory for building a DecisionEvent."""
    return DecisionEvent(
        event_type=event_type,
        timestamp=timestamp,
        metadata=metadata or {},
    )
