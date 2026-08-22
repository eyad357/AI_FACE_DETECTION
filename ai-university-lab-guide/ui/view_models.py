"""
UI-owned view models for the Route Display presentation layer.

Responsibility: define the plain, framework-independent data shapes the
UI renders. These are display-ready structures — they hold no
behavior beyond input validation, perform no route calculation, no
pathfinding, no intent classification, and no hardware access.

Why these live in app.ui rather than app/models/schemas.py
------------------------------------------------------------
app/models/schemas.py is the canonical cross-module contract store
(see docs/integration_contract.md), but as of this phase it defines
only Vision (`DetectionResult`/`FaceDetection`/`BoundingBox`) and ML
(`IntentResult`) contracts. There is no `RouteResult`, `RouteStep`, or
`PlaceInfo` contract there because `app.navigation` is still an
unimplemented placeholder (see app/navigation/__init__.py,
app/navigation/service.py, app/navigation/pathfinder.py,
app/navigation/map_data.py — all docstring-only, no logic, no
`RouteRequest`/`RouteResult` type exists anywhere in the project yet).

Per the integration contract's existing precedent — `GuideResponse`
lives in `app.guide.guide_service` rather than `app/models/schemas.py`
because it is the *producing* module's own contract — a route/place
contract that Navigation has not yet published belongs, for now, to
the *consuming* module (UI) as an adapter-owned view model, not as an
invented addition to the shared schema file. When app.navigation
publishes a real `RouteResult`, a small adapter function (see
app.ui.route_display) can translate it into these view models without
any change to this file's public shape being required.

SystemStatus is UI-owned for the same reason: it is a distinct,
route/interaction-oriented vocabulary (WAITING, LISTENING, PROCESSING,
NAVIGATING, ARRIVED, ERROR) that only partially overlaps with
app.decision.event_manager.ApplicationState (WAITING, GREETING,
GUIDE_MENU, EXPLAINING, COOLDOWN, ERROR) and is not a superset or
subset of it. Reusing ApplicationState directly would either be
missing required values (LISTENING, PROCESSING, NAVIGATING, ARRIVED)
or silently redefine Decision's existing enum, so a separate,
UI-scoped enum is used instead.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class SystemStatus(Enum):
    """
    UI-facing system status vocabulary.

    Distinct from app.decision.event_manager.ApplicationState (see
    module docstring for why this is not a duplicate/replacement of
    that enum).
    """

    WAITING = "WAITING"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    NAVIGATING = "NAVIGATING"
    ARRIVED = "ARRIVED"
    ERROR = "ERROR"


@dataclass(frozen=True)
class RouteStep:
    """
    A single step of a route's turn-by-turn instructions.

    Attributes:
        index: 1-based position of this step within the route.
        instruction: Human-readable instruction text (e.g. "Turn left
            at the main hallway").
        distance_meters: Distance covered by this step, if known.
        duration_seconds: Estimated time for this step, if known.
    """

    index: int
    instruction: str
    distance_meters: Optional[float] = None
    duration_seconds: Optional[float] = None

    def __post_init__(self) -> None:
        if self.index < 1:
            raise ValueError(f"RouteStep.index must be >= 1, got {self.index}")
        if not self.instruction or not self.instruction.strip():
            raise ValueError("RouteStep.instruction must not be empty")
        if self.distance_meters is not None and self.distance_meters < 0:
            raise ValueError(
                f"RouteStep.distance_meters must be >= 0, got "
                f"{self.distance_meters}"
            )
        if self.duration_seconds is not None and self.duration_seconds < 0:
            raise ValueError(
                f"RouteStep.duration_seconds must be >= 0, got "
                f"{self.duration_seconds}"
            )


@dataclass(frozen=True)
class PlaceInfoView:
    """
    Display-ready information about a place/destination, when
    available. All fields beyond `name` are optional because place
    metadata may not always be provided by an upstream source.
    """

    name: str
    description: Optional[str] = None
    category: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("PlaceInfoView.name must not be empty")


@dataclass(frozen=True)
class RouteView:
    """
    Display-ready route information.

    Attributes:
        destination_name: Name of the destination for this route.
        steps: Ordered turn-by-turn instructions. May be empty for a
            route with no intermediate steps (e.g. "you are already
            there" or a single-hop route).
        total_distance_meters: Total route distance, if provided by
            Navigation.
        total_duration_seconds: Total estimated route duration, if
            provided by Navigation.
        current_step_index: 1-based index of the step currently being
            followed, if navigation is in progress. None when not
            actively navigating (e.g. before start, or after arrival).
    """

    destination_name: str
    steps: List[RouteStep] = field(default_factory=list)
    total_distance_meters: Optional[float] = None
    total_duration_seconds: Optional[float] = None
    current_step_index: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.destination_name or not self.destination_name.strip():
            raise ValueError("RouteView.destination_name must not be empty")
        if self.total_distance_meters is not None and self.total_distance_meters < 0:
            raise ValueError(
                f"RouteView.total_distance_meters must be >= 0, got "
                f"{self.total_distance_meters}"
            )
        if self.total_duration_seconds is not None and self.total_duration_seconds < 0:
            raise ValueError(
                f"RouteView.total_duration_seconds must be >= 0, got "
                f"{self.total_duration_seconds}"
            )
        if self.current_step_index is not None:
            if self.current_step_index < 1:
                raise ValueError(
                    f"RouteView.current_step_index must be >= 1, got "
                    f"{self.current_step_index}"
                )
            if self.steps and self.current_step_index > len(self.steps):
                raise ValueError(
                    f"RouteView.current_step_index={self.current_step_index} "
                    f"exceeds step count={len(self.steps)}"
                )


@dataclass(frozen=True)
class GuideContentView:
    """
    Display-ready adapter over app.guide.guide_service.GuideResponse.

    Kept as a thin, additive UI-side wrapper rather than rendering
    GuideResponse directly, so the renderer only ever depends on
    app.ui view models — never reaches back into app.guide's own
    contract types.
    """

    title: str
    summary: str
    sections: List[str] = field(default_factory=list)
    spoken_text: str = ""

    def __post_init__(self) -> None:
        if not self.title or not self.title.strip():
            raise ValueError("GuideContentView.title must not be empty")


@dataclass(frozen=True)
class NavigationView:
    """
    Top-level aggregate view model for the Route Display UI.

    This is the single object the renderer needs to draw a full
    screen: current system status, destination, route detail, place
    information, and an optional human-readable message (used for
    error/unknown-destination/arrival messaging).

    Attributes:
        status: Current system status.
        destination_name: Name of the requested/active destination, if
            any.
        route: Route detail, if a route is available.
        place_info: Place information, if available.
        message: Optional short human-readable message (e.g. an error
            description or an arrival confirmation). Always a plain
            string — the UI never renders raw exceptions.
    """

    status: SystemStatus
    destination_name: Optional[str] = None
    route: Optional[RouteView] = None
    place_info: Optional[PlaceInfoView] = None
    message: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, SystemStatus):
            raise ValueError(
                f"NavigationView.status must be a SystemStatus, got "
                f"{type(self.status).__name__}"
            )
