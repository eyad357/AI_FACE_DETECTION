"""
Public Navigation API.

    from app.navigation.service import NavigationService
    from app.navigation.contracts import RouteRequest

    navigation = NavigationService()
    result = navigation.find_route(RouteRequest(origin="entrance", destination="ai lab"))

Responsibility: "How do I get from A to B in the lab/building?" —
nothing more. NavigationService never drives the robot itself and never
renders UI; see docs/navigation.md for the full integration boundary
with app.ui and a future Robot Integration Adapter / orchestration
layer.

Dependency rules (enforced by tests/navigation/test_dependency_isolation.py):
    - MUST NOT import app.robot, app.vision, app.ml, app.dl, app.speech,
      app.decision, app.ui, or app.main
    - MAY use app.models for shared contracts it does not own
    - MAY use app.config for centralized configuration
    - MAY use app.utils.logger for logging
"""

from __future__ import annotations

from typing import Optional

from app.navigation.contracts import (
    LocationId,
    RouteFailureReason,
    RouteRequest,
    RouteResult,
    RouteStep,
    RouteStepAction,
)
from app.navigation.map_data import DEFAULT_MAP, NavigationMap
from app.navigation.pathfinder import find_shortest_path
from app.utils.logger import get_logger

logger = get_logger(__name__)


class NavigationService:
    """
    Navigation's public entry point.

    A thin, stateless orchestration layer over ``NavigationMap`` (data)
    and ``pathfinder`` (algorithm): it resolves the request's
    origin/destination strings to canonical location ids, delegates to
    the pathfinder, and translates the result into a ``RouteResult``.
    It owns no route-computation logic of its own.
    """

    def __init__(self, nav_map: Optional[NavigationMap] = None) -> None:
        """
        Args:
            nav_map: The map to route over. Defaults to
                ``app.navigation.map_data.DEFAULT_MAP``. Overridable so
                tests (and any future deployment with a different
                building layout) do not have to mutate global state.
        """
        self._map = nav_map if nav_map is not None else DEFAULT_MAP

    def resolve_destination(self, name_or_alias: str) -> Optional[LocationId]:
        """
        Resolve a free-text destination name/alias to a canonical
        location id, without computing a route.

        This is Navigation's documented destination-resolution
        boundary (see docs/navigation.md, "Destination Resolution"): a
        future orchestrator that receives a destination string from
        Speech can call this directly to validate/normalize it before
        building a RouteRequest, without Navigation ever importing
        app.speech.

        Returns:
            The canonical LocationId, or None if unrecognized.
        """
        return self._map.resolve(name_or_alias)

    def find_route(self, request: RouteRequest) -> RouteResult:
        """
        Compute a route for the given request.

        Never raises for expected navigation outcomes (unknown
        locations, unreachable destinations, malformed requests) — all
        of those are reported as a structured, unsuccessful
        RouteResult. See docs/navigation.md, "Error Handling".

        Args:
            request: The origin/destination to route between. Values
                may be canonical location ids, display names, or known
                aliases (case-insensitive).

        Returns:
            A RouteResult. success=True with an ordered, non-negative
            list of RouteStep on success (empty only when origin and
            destination resolve to the same location); success=False
            with a RouteFailureReason and a human-readable message
            otherwise.
        """
        if not isinstance(request, RouteRequest) or not request.is_valid:
            logger.info("Rejected invalid route request: %r", request)
            return RouteResult(
                success=False,
                origin=getattr(request, "origin", "") or "",
                destination=getattr(request, "destination", "") or "",
                failure_reason=RouteFailureReason.INVALID_REQUEST,
                message="Both origin and destination are required.",
            )

        origin_id = self._map.resolve(request.origin)
        if origin_id is None:
            logger.info("Unknown origin in route request: %r", request.origin)
            return RouteResult(
                success=False,
                origin=request.origin,
                destination=request.destination,
                failure_reason=RouteFailureReason.UNKNOWN_ORIGIN,
                message=f"Unknown origin: {request.origin!r}",
            )

        destination_id = self._map.resolve(request.destination)
        if destination_id is None:
            logger.info(
                "Unknown destination in route request: %r", request.destination
            )
            return RouteResult(
                success=False,
                origin=request.origin,
                destination=request.destination,
                failure_reason=RouteFailureReason.UNKNOWN_DESTINATION,
                message=f"Unknown destination: {request.destination!r}",
            )

        path = find_shortest_path(self._map, origin_id, destination_id)
        if path is None:
            logger.info(
                "No path between %r and %r", origin_id, destination_id
            )
            return RouteResult(
                success=False,
                origin=request.origin,
                destination=request.destination,
                failure_reason=RouteFailureReason.UNREACHABLE,
                message=(
                    f"No route exists between {request.origin!r} and "
                    f"{request.destination!r}."
                ),
            )

        steps = _build_steps(self._map, path.location_ids)
        logger.info(
            "Route found: %s -> %s (%d step(s), distance=%s)",
            origin_id,
            destination_id,
            len(steps),
            path.total_distance,
        )
        return RouteResult(
            success=True,
            origin=request.origin,
            destination=request.destination,
            steps=steps,
            total_distance=path.total_distance,
            message=(
                "You are already at the destination."
                if origin_id == destination_id
                else None
            ),
        )


def _build_steps(nav_map: NavigationMap, location_ids: list) -> list:
    """
    Translate an ordered list of location ids into semantic RouteStep
    objects, one per hop, with each hop's own edge distance looked up
    from the map. Internal helper — not part of the public API.
    """
    if len(location_ids) <= 1:
        return []

    hop_count = len(location_ids) - 1
    steps = []
    for sequence, (from_id, to_id) in enumerate(
        zip(location_ids, location_ids[1:]), start=1
    ):
        is_last = sequence == hop_count
        action = RouteStepAction.ARRIVE if is_last else (
            RouteStepAction.DEPART if sequence == 1 else RouteStepAction.PROCEED
        )
        hop_distance = nav_map.neighbors(from_id)[to_id]
        steps.append(
            RouteStep(
                sequence=sequence,
                from_location=from_id,
                to_location=to_id,
                action=action,
                distance=hop_distance,
            )
        )

    return steps
