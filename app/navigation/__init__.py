"""
Navigation module — "How do I get from A to B?" for the AI University
Lab Guide Robot.

Owner: Person 1 (AI / Intelligence).

Public API:

    from app.navigation.service import NavigationService
    from app.navigation.contracts import RouteRequest, RouteResult, RouteStep

    navigation = NavigationService()
    result = navigation.find_route(RouteRequest(origin="entrance", destination="ai lab"))

Architecture:

    RouteRequest
          |
          v
    NavigationService  (app.navigation.service)
          |
          v
    find_shortest_path (app.navigation.pathfinder, Dijkstra over
                         app.navigation.map_data.NavigationMap)
          |
          v
    RouteResult
          |
          v
    UI Adapter / Robot Integration Adapter / future orchestration layer

Submodules:
    contracts.py  — RouteRequest / RouteResult / RouteStep / Destination
                     (Navigation's own public contracts; see docs/navigation.md)
    map_data.py   — deterministic weighted location graph (NavigationMap)
    pathfinder.py — Dijkstra shortest-path search over NavigationMap
    service.py    — NavigationService, the module's public entry point

Dependency rules (enforced by tests/navigation/test_dependency_isolation.py):
    Navigation MUST NOT import app.robot, app.vision, app.ml, app.dl,
    app.speech, app.decision, app.ui, or app.main.
    Navigation communicates via its own contracts (app.navigation.contracts),
    optionally alongside app.models for contracts it does not own.

This package is NOT connected to app.robot or app.main in this phase —
see docs/navigation.md for the documented future integration contract.
"""

from app.navigation.contracts import (
    Destination,
    LocationId,
    RouteFailureReason,
    RouteRequest,
    RouteResult,
    RouteStep,
    RouteStepAction,
)
from app.navigation.service import NavigationService

__all__ = [
    "Destination",
    "LocationId",
    "RouteFailureReason",
    "RouteRequest",
    "RouteResult",
    "RouteStep",
    "RouteStepAction",
    "NavigationService",
]
