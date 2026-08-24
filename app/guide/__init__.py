"""
Guide layer.

Responsibility: answer "what information should be provided?" Given a
topic (app.decision.event_manager.GuideTopic), GuideService returns a
structured GuideResponse built from static content in
app.guide.content.

This package MUST NOT import app.vision, app.robot, or
app.decision.state_manager. It imports exactly one symbol from
app.decision — the existing GuideTopic enum — to avoid duplicating that
contract. See docs/integration_contract.md for the full dependency
rules.
"""

from app.guide.guide_service import GuideResponse, GuideService

__all__ = ["GuideResponse", "GuideService"]
