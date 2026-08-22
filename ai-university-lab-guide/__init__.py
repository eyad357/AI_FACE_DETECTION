"""
Robot Integration Adapter layer.

Responsibility: translate high-level, application-level Robot-facing
actions into calls against the existing, unmodified `app.robot` public
API. This package is a thin translation boundary — it is not an
orchestrator, not a decision engine, not an intent classifier, and not
a second Robot controller. See `app/integration/robot_adapter.py` and
`docs/robot_integration_adapter.md` for the full design.

This package MUST NOT import app.vision, app.ml, or app.dl, and avoids
importing app.decision, app.guide, app.navigation, and app.main. See
`docs/robot_integration_adapter.md` for the full dependency rules.
"""

from app.integration.robot_adapter import AdapterError, RobotIntegrationAdapter

__all__ = [
    "RobotIntegrationAdapter",
    "AdapterError",
]
