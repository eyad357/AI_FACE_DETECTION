"""
Decision layer.

Responsibility: consume app.models.schemas.DetectionResult objects
(produced upstream by Vision) and produce application-level
DecisionEvent objects plus ApplicationState transitions — i.e. answer
"what should the application do next?"

This package MUST NOT import app.vision or app.robot. It depends only
on the Python standard library, app.models, app.config, and
app.utils.logger. See docs/integration_contract.md for the full
dependency rules.
"""

from app.decision.event_manager import (
    ApplicationState,
    DecisionEvent,
    DecisionEventType,
    GuideTopic,
    create_event,
)
from app.decision.state_manager import StateManager

__all__ = [
    "ApplicationState",
    "DecisionEvent",
    "DecisionEventType",
    "GuideTopic",
    "create_event",
    "StateManager",
]
