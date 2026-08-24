"""
Guide adapter for the dashboard.

Wraps app.guide.guide_service.GuideService and reuses the existing
app.ui.route_display.guide_response_to_view adapter (rather than
duplicating the GuideResponse -> GuideContentView translation) to
produce the dashboard's display-ready content.
"""

from __future__ import annotations

from typing import Optional

from app.decision.event_manager import GuideTopic
from app.guide.guide_service import GuideService
from app.ui.dashboard_view_models import HealthState, SubsystemStatus
from app.ui.route_display import guide_response_to_view
from app.ui.view_models import GuideContentView
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GuideAdapter:
    """Dashboard-facing wrapper around the real Guide service."""

    def __init__(self) -> None:
        self._service: Optional[GuideService] = None
        self._init_error: Optional[str] = None
        try:
            self._service = GuideService()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Guide unavailable: %s", exc)
            self._init_error = str(exc)

    def status(self) -> SubsystemStatus:
        if self._service is None:
            return SubsystemStatus(
                name="Guide",
                state=HealthState.UNAVAILABLE,
                detail=self._init_error or "Guide service failed to initialize",
            )
        return SubsystemStatus(name="Guide", state=HealthState.PASS, detail="Content service ready")

    def get_topic_view(self, topic: GuideTopic) -> Optional[GuideContentView]:
        if self._service is None:
            return None
        response = self._service.get_topic_content(topic)
        return guide_response_to_view(response)
