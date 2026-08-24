"""
Route Display adapters/builders.

Responsibility: turn raw, already-decided data (destination names,
step instructions, distances/durations, a GuideResponse) into the
display-ready view models defined in app.ui.view_models. This module
does not calculate routes, does not perform pathfinding, does not
classify intents, and does not decide what should be displayed next —
it only shapes whatever it is given into a renderable form, plus safe,
controlled fallbacks for missing/invalid input (mirroring the pattern
already used by app.guide.guide_service.GuideService for unknown
topics: never raise for normal invalid/missing user-facing input).

Dependencies
------------
This module imports only:
    - app.ui.view_models (this phase's own view models)
    - app.guide.guide_service.GuideResponse (existing, stable contract
      — see docs/integration_contract.md: "UI -> Models, Guide")
    - app.utils.logger (existing, stable utility)

It does NOT import app.navigation (still an unimplemented placeholder
— see the module docstring in app/ui/view_models.py for the full
rationale), app.robot, app.vision, app.ml, app.dl, or app.main.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from app.guide.guide_service import GuideResponse
from app.ui.view_models import (
    GuideContentView,
    NavigationView,
    PlaceInfoView,
    RouteStep,
    RouteView,
    SystemStatus,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

_UNKNOWN_DESTINATION_MESSAGE = "This destination is not currently available."
_EMPTY_DESTINATION_MESSAGE = "No destination has been set."
_GENERIC_ERROR_MESSAGE = "Something went wrong while preparing route information."


def build_route_view(
    destination_name: str,
    steps: Optional[Sequence[Tuple[str, Optional[float], Optional[float]]]] = None,
    total_distance_meters: Optional[float] = None,
    total_duration_seconds: Optional[float] = None,
    current_step_index: Optional[int] = None,
) -> RouteView:
    """
    Build a RouteView from plain, primitive route data.

    Args:
        destination_name: Name of the destination.
        steps: Ordered sequence of
            (instruction, distance_meters, duration_seconds) tuples.
            distance_meters/duration_seconds may be None per step.
            Defaults to an empty route (no intermediate steps).
        total_distance_meters: Total route distance, if known.
        total_duration_seconds: Total estimated route duration, if
            known.
        current_step_index: 1-based index of the step currently being
            followed, if any.

    Raises:
        ValueError: If the resulting RouteView would be invalid (e.g.
            empty destination name, negative distance/duration, an
            out-of-range current_step_index, or a malformed step
            tuple). Callers that receive user-facing/external input
            should prefer `build_navigation_view_safe` below, which
            converts this into a controlled ERROR NavigationView
            instead of propagating the exception.
    """
    route_steps: List[RouteStep] = []
    for position, step in enumerate(steps or (), start=1):
        try:
            instruction, distance_meters, duration_seconds = step
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Malformed route step at position {position}: {step!r} "
                f"(expected a 3-item tuple of "
                f"(instruction, distance_meters, duration_seconds))"
            ) from exc
        route_steps.append(
            RouteStep(
                index=position,
                instruction=instruction,
                distance_meters=distance_meters,
                duration_seconds=duration_seconds,
            )
        )

    return RouteView(
        destination_name=destination_name,
        steps=route_steps,
        total_distance_meters=total_distance_meters,
        total_duration_seconds=total_duration_seconds,
        current_step_index=current_step_index,
    )


def build_place_info_view(
    name: str,
    description: Optional[str] = None,
    category: Optional[str] = None,
) -> PlaceInfoView:
    """Build a PlaceInfoView from plain place data."""
    return PlaceInfoView(name=name, description=description, category=category)


def unknown_destination_view(requested_name: Optional[str] = None) -> NavigationView:
    """
    A controlled NavigationView for a destination that could not be
    resolved, mirroring GuideService's "Topic Unavailable" pattern:
    never raise for normal invalid/unknown user input.
    """
    logger.warning("Unknown destination requested: %r", requested_name)
    return NavigationView(
        status=SystemStatus.ERROR,
        destination_name=requested_name,
        message=_UNKNOWN_DESTINATION_MESSAGE,
    )


def empty_destination_view() -> NavigationView:
    """A controlled NavigationView for when no destination is set yet."""
    return NavigationView(
        status=SystemStatus.WAITING,
        destination_name=None,
        message=_EMPTY_DESTINATION_MESSAGE,
    )


def navigating_view(route: RouteView) -> NavigationView:
    """A NavigationView representing an in-progress navigation."""
    return NavigationView(
        status=SystemStatus.NAVIGATING,
        destination_name=route.destination_name,
        route=route,
    )


def arrived_view(
    destination_name: str, place_info: Optional[PlaceInfoView] = None
) -> NavigationView:
    """A NavigationView representing arrival at the destination."""
    return NavigationView(
        status=SystemStatus.ARRIVED,
        destination_name=destination_name,
        place_info=place_info,
        message=f"You have arrived at {destination_name}.",
    )


def error_view(message: Optional[str] = None) -> NavigationView:
    """A controlled NavigationView for a system error state."""
    return NavigationView(
        status=SystemStatus.ERROR,
        message=message or _GENERIC_ERROR_MESSAGE,
    )


def build_navigation_view_safe(
    destination_name: Optional[str],
    steps: Optional[Sequence[Tuple[str, Optional[float], Optional[float]]]] = None,
    total_distance_meters: Optional[float] = None,
    total_duration_seconds: Optional[float] = None,
    current_step_index: Optional[int] = None,
    place_info: Optional[PlaceInfoView] = None,
) -> NavigationView:
    """
    Build a NavigationView from plain route data, never raising for
    normal invalid/malformed input.

    - A missing/blank destination_name produces `empty_destination_view()`.
    - Malformed step data or invalid numeric fields (negative
      distance/duration, an out-of-range current_step_index, etc.)
      produce a controlled `error_view(...)` rather than propagating
      the underlying ValueError.
    - Otherwise, produces a `navigating_view(...)` built from the
      given data.
    """
    if destination_name is None or not destination_name.strip():
        return empty_destination_view()

    try:
        route = build_route_view(
            destination_name=destination_name,
            steps=steps,
            total_distance_meters=total_distance_meters,
            total_duration_seconds=total_duration_seconds,
            current_step_index=current_step_index,
        )
    except ValueError as exc:
        logger.error("Failed to build route view for %r: %s", destination_name, exc)
        return error_view(str(exc))

    view = navigating_view(route)
    if place_info is not None:
        view = NavigationView(
            status=view.status,
            destination_name=view.destination_name,
            route=view.route,
            place_info=place_info,
            message=view.message,
        )
    return view


def guide_response_to_view(response: GuideResponse) -> GuideContentView:
    """
    Adapt an existing app.guide.guide_service.GuideResponse into a
    display-ready GuideContentView.

    This performs no content generation — GuideService remains the
    sole owner of guide content (see docs/integration_contract.md).
    """
    return GuideContentView(
        title=response.title,
        summary=response.summary,
        sections=list(response.sections),
        spoken_text=response.spoken_text,
    )
