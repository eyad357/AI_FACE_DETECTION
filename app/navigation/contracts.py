"""
Public typed contracts for the Navigation module.

This is the SINGLE SOURCE OF TRUTH for Navigation's cross-module data
structures — ``RouteRequest``, ``RouteResult``, ``RouteStep``,
``Destination``, and ``RouteFailureReason``. Following the precedent
already established for other producer-owned contracts in this project
(``DecisionEvent`` in ``app.decision.event_manager``, ``GuideResponse``
in ``app.guide.guide_service``, ``RobotExecutionResult`` in
``app.robot.robot_controller`` — see docs/contracts.md), these types
live in the module that produces them (``app.navigation``) rather than
being added to ``app/models/schemas.py``.

Consumers (UI, a future orchestration/integration layer, a future
Robot Integration Adapter extension) import these types from here:

    from app.navigation.contracts import RouteRequest, RouteResult

This module has no dependencies beyond the Python standard library. It
MUST NOT import from app.ui, app.robot, app.speech, app.decision,
app.vision, app.ml, app.dl, or app.main, so that it can safely be
imported from anywhere in the application without creating circular
imports (mirroring the rule already documented at the top of
app/models/schemas.py for the same reason).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

# A canonical location identifier. Plain string (not an Enum) by
# design, matching the precedent set by app.guide.locations.LocationId:
# the set of known locations is open-ended map data, not a fixed
# vocabulary, so adding/renaming a location is a pure data change
# rather than a change to a shared Enum contract.
LocationId = str


class RouteFailureReason(Enum):
    """
    Structured reason a route could not be produced.

    Used instead of raising generic exceptions for expected, normal
    navigation outcomes (see docs/navigation.md, "Error Handling").
    Exceptions are reserved for programmer/configuration errors (e.g.
    a malformed map passed to NavigationService.__init__), not for
    ordinary "this destination doesn't exist" situations.
    """

    UNKNOWN_ORIGIN = "UNKNOWN_ORIGIN"
    UNKNOWN_DESTINATION = "UNKNOWN_DESTINATION"
    UNREACHABLE = "UNREACHABLE"
    INVALID_REQUEST = "INVALID_REQUEST"


class RouteStepAction(Enum):
    """Semantic action a single RouteStep represents."""

    DEPART = "DEPART"
    PROCEED = "PROCEED"
    ARRIVE = "ARRIVE"


@dataclass(frozen=True)
class Destination:
    """
    A resolved place Navigation can route to or from.

    Attributes:
        location_id: Canonical identifier (see LocationId).
        name: Human-readable display name.
    """

    location_id: LocationId
    name: str

    def __post_init__(self) -> None:
        if not self.location_id or not self.location_id.strip():
            raise ValueError("Destination.location_id must not be empty")
        if not self.name or not self.name.strip():
            raise ValueError("Destination.name must not be empty")


@dataclass(frozen=True)
class RouteRequest:
    """
    Minimum information required to calculate a route.

    Attributes:
        origin: Canonical location id or a known alias/display name of
            the starting point (case-insensitive; see
            docs/navigation.md, "Destination Resolution").
        destination: Canonical location id or a known alias/display
            name of the desired destination.
    """

    origin: str
    destination: str

    def __post_init__(self) -> None:
        # Deliberately does not raise here: an empty origin/destination
        # is a normal, expected "invalid request" outcome that
        # NavigationService.find_route reports via
        # RouteResult(success=False, failure_reason=INVALID_REQUEST),
        # not a programmer error. Raising in __post_init__ would force
        # every caller to wrap construction in try/except for an
        # everyday user-input case.
        pass

    @property
    def is_valid(self) -> bool:
        """True if both origin and destination are non-empty strings."""
        return bool(self.origin and self.origin.strip()) and bool(
            self.destination and self.destination.strip()
        )


@dataclass(frozen=True)
class RouteStep:
    """
    A single semantic step of a computed route.

    Attributes:
        sequence: 1-based position of this step within the route.
        from_location: Canonical location id this step starts from.
        to_location: Canonical location id this step ends at.
        action: Semantic action this step represents.
        distance: Cost/distance covered by this step, in the map's
            distance unit (see docs/navigation.md). Always >= 0.
    """

    sequence: int
    from_location: LocationId
    to_location: LocationId
    action: RouteStepAction
    distance: float

    def __post_init__(self) -> None:
        if self.sequence < 1:
            raise ValueError(f"RouteStep.sequence must be >= 1, got {self.sequence}")
        if not self.from_location or not self.from_location.strip():
            raise ValueError("RouteStep.from_location must not be empty")
        if not self.to_location or not self.to_location.strip():
            raise ValueError("RouteStep.to_location must not be empty")
        if not isinstance(self.action, RouteStepAction):
            raise ValueError(
                f"RouteStep.action must be a RouteStepAction, got "
                f"{type(self.action).__name__}"
            )
        if self.distance < 0:
            raise ValueError(f"RouteStep.distance must be >= 0, got {self.distance}")


@dataclass(frozen=True)
class RouteResult:
    """
    Output of NavigationService.find_route.

    Exactly one of two shapes is valid:
      - success=True: steps/total_distance are populated (steps may be
        empty only when origin == destination), failure_reason is None.
      - success=False: steps is empty, total_distance is None,
        failure_reason is set, message explains why in human terms.

    Attributes:
        success: Whether a route was found.
        origin: The origin exactly as given in the request (not the
            resolved canonical id — see docs/navigation.md for why).
        destination: The destination exactly as given in the request.
        steps: Ordered route steps. Empty when origin resolves to the
            same location as destination, or on failure.
        total_distance: Sum of all step distances, if successful.
        failure_reason: Structured reason, set only when success=False.
        message: Optional short human-readable explanation, safe to
            surface to a user/UI directly (never a raw exception).
    """

    success: bool
    origin: str
    destination: str
    steps: List[RouteStep] = field(default_factory=list)
    total_distance: Optional[float] = None
    failure_reason: Optional[RouteFailureReason] = None
    message: Optional[str] = None

    def __post_init__(self) -> None:
        if self.success:
            if self.failure_reason is not None:
                raise ValueError(
                    "RouteResult.failure_reason must be None when success=True"
                )
            if self.total_distance is not None and self.total_distance < 0:
                raise ValueError(
                    f"RouteResult.total_distance must be >= 0, got "
                    f"{self.total_distance}"
                )
        else:
            if self.failure_reason is None:
                raise ValueError(
                    "RouteResult.failure_reason must be set when success=False"
                )
            if self.steps:
                raise ValueError("RouteResult.steps must be empty when success=False")
            if self.total_distance is not None:
                raise ValueError(
                    "RouteResult.total_distance must be None when success=False"
                )
        for expected_index, step in enumerate(self.steps, start=1):
            if step.sequence != expected_index:
                raise ValueError(
                    f"RouteResult.steps must be ordered 1..N with no gaps; "
                    f"expected sequence={expected_index}, got {step.sequence}"
                )
