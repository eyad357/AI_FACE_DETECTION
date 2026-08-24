"""
Pathfinding over app.navigation.map_data.NavigationMap.

## Algorithm choice: Dijkstra

The map (app.navigation.map_data.NavigationMap) is a weighted graph —
edges carry a "distance" cost that varies per connection (e.g.
main_hallway -> ai_lab is 15, main_hallway -> main_auditorium is 30).
Plain BFS finds the path with the *fewest hops*, which is not
necessarily the path with the least total distance on a weighted graph
(a two-hop path can easily be longer than a three-hop one here). A*
would additionally require an admissible distance heuristic between
arbitrary locations (e.g. real coordinates), which this prototype map
does not have. Dijkstra is the simplest algorithm that is still
*correct* for "shortest total distance on a non-negative-weight graph"
given the data actually available, so it is what this module
implements. All edge weights in map_data.py are validated to be
strictly positive at map-construction time, which is exactly Dijkstra's
correctness precondition.

If real-world coordinates are added to the map in a future phase, A*
becomes a reasonable upgrade — this module's public function signature
(``find_shortest_path``) would not need to change for that.

## Determinism

Given the same map and the same (origin, destination) pair, this
implementation always returns the same result. Python's heapq is a
stable min-heap, but ties between equal-priority entries are broken
explicitly by canonical location id (see ``_QueueEntry``) rather than
left to insertion order, so results do not depend on dict/set iteration
order.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.navigation.contracts import LocationId
from app.navigation.map_data import NavigationMap


@dataclass(order=True)
class _QueueEntry:
    """Priority-queue entry ordered by (distance, location_id) for a
    fully deterministic tie-break regardless of insertion order."""

    priority: float
    location_id: LocationId = field(compare=True)


@dataclass(frozen=True)
class PathResult:
    """
    Result of a successful shortest-path search.

    Attributes:
        location_ids: Ordered path from origin to destination,
            inclusive of both endpoints. Length 1 when origin ==
            destination.
        total_distance: Sum of edge distances along the path. 0 when
            origin == destination.
    """

    location_ids: List[LocationId]
    total_distance: float


def find_shortest_path(
    nav_map: NavigationMap, origin: LocationId, destination: LocationId
) -> Optional[PathResult]:
    """
    Compute the least-total-distance path between two known locations.

    Args:
        nav_map: The map to search over.
        origin: Canonical location id (must already be resolved — this
            function does not do alias/name resolution).
        destination: Canonical location id (must already be resolved).

    Returns:
        A PathResult, or None if no path exists (the destination is
        unreachable from the origin).

    Raises:
        KeyError: If ``origin`` or ``destination`` is not a known
            location id in ``nav_map``. Resolving user-facing names to
            canonical ids (and reporting UNKNOWN_ORIGIN /
            UNKNOWN_DESTINATION as structured failures) is
            NavigationService's job, not this function's — by the time
            this function is called, both ids are expected to already
            be valid, so an unknown id here is a programmer error.
    """
    if not nav_map.has_location(origin):
        raise KeyError(f"Unknown origin location_id: {origin}")
    if not nav_map.has_location(destination):
        raise KeyError(f"Unknown destination location_id: {destination}")

    if origin == destination:
        return PathResult(location_ids=[origin], total_distance=0.0)

    distances: Dict[LocationId, float] = {origin: 0.0}
    previous: Dict[LocationId, LocationId] = {}
    visited: set = set()
    queue: List[_QueueEntry] = [_QueueEntry(0.0, origin)]

    while queue:
        current = heapq.heappop(queue)
        if current.location_id in visited:
            continue
        visited.add(current.location_id)

        if current.location_id == destination:
            break

        for neighbor_id, edge_distance in sorted(
            nav_map.neighbors(current.location_id).items()
        ):
            if neighbor_id in visited:
                continue
            candidate = distances[current.location_id] + edge_distance
            if candidate < distances.get(neighbor_id, float("inf")):
                distances[neighbor_id] = candidate
                previous[neighbor_id] = current.location_id
                heapq.heappush(queue, _QueueEntry(candidate, neighbor_id))

    if destination not in distances:
        return None

    # Reconstruct the path by walking `previous` backwards from the
    # destination to the origin.
    path: List[LocationId] = [destination]
    while path[-1] != origin:
        path.append(previous[path[-1]])
    path.reverse()

    return PathResult(location_ids=path, total_distance=distances[destination])
