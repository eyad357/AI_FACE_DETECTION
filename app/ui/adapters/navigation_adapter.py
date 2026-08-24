"""
Navigation adapter for the dashboard.

Wraps app.navigation.service.NavigationService and translates its real
RouteResult into the existing app.ui.view_models.NavigationView via the
existing app.ui.route_display.build_navigation_view_safe builder --
never a second, duplicate route-rendering path.
"""

from __future__ import annotations

from typing import Optional

from app.navigation.contracts import RouteRequest, RouteResult
from app.navigation.service import NavigationService
from app.ui.dashboard_view_models import HealthState, SubsystemStatus
from app.ui.route_display import build_navigation_view_safe, error_view
from app.ui.view_models import NavigationView
from app.utils.logger import get_logger

logger = get_logger(__name__)


class NavigationAdapter:
    """Dashboard-facing wrapper around the real Navigation service."""

    def __init__(self) -> None:
        self._service: Optional[NavigationService] = None
        self._init_error: Optional[str] = None
        try:
            self._service = NavigationService()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Navigation unavailable: %s", exc)
            self._init_error = str(exc)

    def status(self) -> SubsystemStatus:
        if self._service is None:
            return SubsystemStatus(
                name="Navigation",
                state=HealthState.UNAVAILABLE,
                detail=self._init_error or "Navigation service failed to initialize",
            )
        return SubsystemStatus(name="Navigation", state=HealthState.PASS, detail="Route service ready")

    def find_route(self, origin: str, destination: str) -> NavigationView:
        if self._service is None:
            return error_view("Navigation service is unavailable.")

        result: RouteResult = self._service.find_route(
            RouteRequest(origin=origin, destination=destination)
        )
        if not result.success:
            return error_view(result.message or "Route could not be found.")

        steps = [
            (step.action.value.title() + f" to {step.to_location}", step.distance, None)
            for step in result.steps
        ]
        return build_navigation_view_safe(
            destination_name=result.destination,
            steps=steps,
            total_distance_meters=result.total_distance,
        )
