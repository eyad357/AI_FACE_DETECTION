"""
Guide content display.

Original (Phase 1) responsibility: present guide content and/or
detection status to a human-facing screen/interface, depending on
app.models and app.guide, not directly on app.vision or app.robot
internals.

Implemented in this phase: the guide-content half of that
responsibility (adapting an existing app.guide.guide_service
GuideResponse into a display-ready view model) lives in
app.ui.route_display.guide_response_to_view, alongside this phase's
route/navigation/status display adapters, so all UI adapters follow
one consistent pattern:

    Domain Data -> UI View Model/Adapter -> Renderer

This module re-exports that function under its original name for any
caller that imports app.ui.guide_ui directly, without duplicating the
adapter logic.
"""

from __future__ import annotations

from app.ui.route_display import guide_response_to_view
from app.ui.view_models import GuideContentView

__all__ = ["guide_response_to_view", "GuideContentView"]
