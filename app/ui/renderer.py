"""
Route Display renderer.

Responsibility: turn view models (app.ui.view_models) into a
deterministic, human-readable text representation. This is the ONLY
part of the UI phase that formats output for display, and it is
intentionally the sole extension point for future presentation
backends.

    Domain Data
        v
    UI View Model / Adapter   (app.ui.route_display)
        v
    Renderer                  (this module)

`TextRenderer` is the renderer used in this phase (terminal/log
friendly, hardware-free, deterministic — no timestamps, randomness, or
locale-dependent formatting). A future GUI/Web renderer can implement
the same `Renderer` interface without changing view_models.py or
route_display.py.

This module performs no route calculation, no pathfinding, no intent
classification, and no hardware access. It only formats already-built
view models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from app.ui.view_models import (
    GuideContentView,
    NavigationView,
    PlaceInfoView,
    RouteView,
    SystemStatus,
)

_STATUS_LABELS = {
    SystemStatus.WAITING: "Waiting",
    SystemStatus.LISTENING: "Listening",
    SystemStatus.PROCESSING: "Processing",
    SystemStatus.NAVIGATING: "Navigating",
    SystemStatus.ARRIVED: "Arrived",
    SystemStatus.ERROR: "Error",
}


class Renderer(ABC):
    """
    Renderer interface. Implementations turn view models into a
    display representation (a string, for TextRenderer; potentially a
    different type for a future GUI/Web renderer implementing this
    same interface).
    """

    @abstractmethod
    def render_navigation(self, view: NavigationView) -> str:
        """Render a NavigationView (destination/route/status/place info)."""
        raise NotImplementedError

    @abstractmethod
    def render_guide(self, view: GuideContentView) -> str:
        """Render a GuideContentView (guide topic content)."""
        raise NotImplementedError

    @abstractmethod
    def render_status(self, status: SystemStatus) -> str:
        """Render a bare system status line."""
        raise NotImplementedError


def _format_distance(distance_meters: float) -> str:
    if distance_meters >= 1000:
        return f"{distance_meters / 1000:.1f} km"
    return f"{distance_meters:.0f} m"


def _format_duration(duration_seconds: float) -> str:
    minutes, seconds = divmod(int(round(duration_seconds)), 60)
    if minutes >= 1:
        return f"{minutes} min {seconds} s"
    return f"{seconds} s"


def _render_route_lines(route: RouteView) -> List[str]:
    lines: List[str] = [f"Destination: {route.destination_name}"]

    summary_parts = []
    if route.total_distance_meters is not None:
        summary_parts.append(_format_distance(route.total_distance_meters))
    if route.total_duration_seconds is not None:
        summary_parts.append(_format_duration(route.total_duration_seconds))
    if summary_parts:
        lines.append("Estimated: " + ", ".join(summary_parts))

    if not route.steps:
        lines.append("Route: (no intermediate steps)")
        return lines

    lines.append("Steps:")
    for step in route.steps:
        marker = "> " if step.index == route.current_step_index else "  "
        detail_parts = []
        if step.distance_meters is not None:
            detail_parts.append(_format_distance(step.distance_meters))
        if step.duration_seconds is not None:
            detail_parts.append(_format_duration(step.duration_seconds))
        detail = f" ({', '.join(detail_parts)})" if detail_parts else ""
        lines.append(f"{marker}{step.index}. {step.instruction}{detail}")

    return lines


def _render_place_info_lines(place_info: PlaceInfoView) -> List[str]:
    lines = [f"Place: {place_info.name}"]
    if place_info.category:
        lines.append(f"Category: {place_info.category}")
    if place_info.description:
        lines.append(place_info.description)
    return lines


class TextRenderer(Renderer):
    """
    Deterministic plain-text renderer. Suitable for a terminal UI or
    logs, and as the reference implementation the next renderer (GUI
    or Web) can be built alongside without touching view models.
    """

    def render_status(self, status: SystemStatus) -> str:
        label = _STATUS_LABELS.get(status)
        if label is None:
            # Defensive: view_models.NavigationView already validates
            # that status is a SystemStatus member, so this should be
            # unreachable in practice. Fail safe rather than raise.
            return "Status: Unknown"
        return f"Status: {label}"

    def render_navigation(self, view: NavigationView) -> str:
        lines: List[str] = [self.render_status(view.status)]

        if view.route is not None:
            lines.extend(_render_route_lines(view.route))
        elif view.destination_name:
            lines.append(f"Destination: {view.destination_name}")

        if view.place_info is not None:
            lines.extend(_render_place_info_lines(view.place_info))

        if view.message:
            lines.append(view.message)

        return "\n".join(lines)

    def render_guide(self, view: GuideContentView) -> str:
        lines: List[str] = [view.title, view.summary]
        lines.extend(view.sections)
        return "\n".join(line for line in lines if line)
