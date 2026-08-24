"""
Deterministic map representation for the Navigation module.

Owns Navigation's location vocabulary and connectivity graph. This is
the ONLY map format in the project — app.navigation.pathfinder and
app.navigation.service both build on top of ``NavigationMap`` rather
than inventing a second representation.

Location identifiers deliberately reuse the same strings as
app.guide.locations.LocationId (e.g. "ai_lab", "robotics_lab") for the
content-bearing locations they have in common, so that a future
orchestration layer can look up Guide content and a Navigation route
for the same place without a translation table. This is a deliberate,
documented choice, not an accidental coupling — see docs/navigation.md,
"Location Vocabulary & Guide Mapping Boundary" for the full rationale
and its limits:

  - Navigation does NOT import app.guide, and app.guide does NOT import
    Navigation. The shared strings are a naming convention, not a code
    dependency.
  - Navigation's graph additionally includes purely structural nodes
    that Guide has no content for (e.g. "entrance", "main_hallway") —
    these exist only to make the map connected/walkable and are never
    valid Guide topics.
  - If a Guide location and a Navigation location ever need to diverge
    (e.g. Guide renames a place without a matching physical move), the
    identifiers may drift apart; nothing in either module enforces they
    stay identical. That is an accepted, documented limitation, not a
    bug.

All map data below is PROTOTYPE / EXAMPLE data (distances are
illustrative, not measured), matching the same disclaimer already given
for app.guide.locations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Tuple

from app.navigation.contracts import LocationId


@dataclass(frozen=True)
class LocationNode:
    """
    A single node in the navigation graph.

    Attributes:
        location_id: Canonical identifier.
        name: Human-readable display name.
        aliases: Additional case-insensitive names/phrases that resolve
            to this location (e.g. "ai lab" -> "ai_lab").
    """

    location_id: LocationId
    name: str
    aliases: Tuple[str, ...] = field(default_factory=tuple)


class NavigationMap:
    """
    A deterministic, weighted, undirected graph of known locations.

    Supports:
        - known locations (``locations`` / ``has_location``)
        - connections between them (``neighbors``)
        - alias/display-name resolution (``resolve``)

    Adding a new location or connection is a pure data change (edit the
    static tables in this module, or construct a new ``NavigationMap``)
    and never requires changing ``app.navigation.pathfinder`` or
    ``app.navigation.service``'s public API.
    """

    def __init__(
        self,
        nodes: List[LocationNode],
        edges: List[Tuple[LocationId, LocationId, float]],
    ) -> None:
        """
        Args:
            nodes: All known locations.
            edges: Undirected connections as (a, b, distance) triples.
                Both directions are added automatically. distance must
                be > 0.

        Raises:
            ValueError: If the map data is internally inconsistent
                (duplicate location ids, duplicate/self/negative-weight
                edges, or an edge referencing an unknown location).
                This is a configuration error, not a normal navigation
                failure, so it is raised eagerly at construction time.
        """
        self._nodes: Dict[LocationId, LocationNode] = {}
        self._alias_index: Dict[str, LocationId] = {}
        self._adjacency: Dict[LocationId, Dict[LocationId, float]] = {}

        for node in nodes:
            if node.location_id in self._nodes:
                raise ValueError(f"Duplicate location_id in map: {node.location_id}")
            self._nodes[node.location_id] = node
            self._adjacency[node.location_id] = {}
            self._register_alias(node.location_id, node.location_id)
            self._register_alias(node.location_id, node.name)
            for alias in node.aliases:
                self._register_alias(node.location_id, alias)

        for a, b, distance in edges:
            if a not in self._nodes:
                raise ValueError(f"Edge references unknown location: {a}")
            if b not in self._nodes:
                raise ValueError(f"Edge references unknown location: {b}")
            if a == b:
                raise ValueError(f"Self-loop edge is not allowed: {a} -> {b}")
            if distance <= 0:
                raise ValueError(
                    f"Edge distance must be > 0, got {distance} for {a} -> {b}"
                )
            if b in self._adjacency[a] or a in self._adjacency[b]:
                raise ValueError(f"Duplicate edge between {a} and {b}")
            self._adjacency[a][b] = distance
            self._adjacency[b][a] = distance

    def _register_alias(self, location_id: LocationId, alias: str) -> None:
        key = alias.strip().lower()
        if not key:
            return
        existing = self._alias_index.get(key)
        if existing is not None and existing != location_id:
            raise ValueError(
                f"Alias {alias!r} is ambiguous between {existing!r} and "
                f"{location_id!r}"
            )
        self._alias_index[key] = location_id

    def has_location(self, location_id: LocationId) -> bool:
        """True if ``location_id`` is a known canonical location id."""
        return location_id in self._nodes

    def resolve(self, name_or_alias: str) -> Optional[LocationId]:
        """
        Resolve a canonical id, display name, or alias to a canonical
        location id, case-insensitively.

        Returns:
            The canonical LocationId, or None if unrecognized.
        """
        if not name_or_alias:
            return None
        return self._alias_index.get(name_or_alias.strip().lower())

    def get_node(self, location_id: LocationId) -> Optional[LocationNode]:
        """Return the LocationNode for a canonical id, or None."""
        return self._nodes.get(location_id)

    def neighbors(self, location_id: LocationId) -> Dict[LocationId, float]:
        """
        Return {neighbor_location_id: distance} for a known location.

        Returns an empty mapping for an isolated (but known) location.

        Raises:
            KeyError: If location_id is not a known location.
        """
        if location_id not in self._adjacency:
            raise KeyError(f"Unknown location_id: {location_id}")
        return dict(self._adjacency[location_id])

    def all_location_ids(self) -> FrozenSet[LocationId]:
        """Return the set of all known canonical location ids."""
        return frozenset(self._nodes.keys())


# ---------------------------------------------------------------------------
# Default prototype map data.
#
# Nodes reuse app.guide.locations' location_id strings for the
# content-bearing places they have in common (see module docstring),
# plus purely structural hub nodes ("entrance", "main_hallway") that
# only exist to make the graph connected. "storage_room" is
# intentionally left disconnected (no edges) so that Navigation has a
# real, deterministic example of a *known but unreachable* location,
# distinct from an *unknown* location — see docs/navigation.md.
# ---------------------------------------------------------------------------

_NODES: List[LocationNode] = [
    LocationNode("entrance", "Main Entrance", ("front door", "main entrance", "lobby")),
    LocationNode("main_hallway", "Main Hallway", ("hallway", "corridor")),
    LocationNode("ai_lab", "AI Lab", ("artificial intelligence lab", "ai laboratory")),
    LocationNode("robotics_lab", "Robotics Lab", ("robotics laboratory", "robot lab")),
    LocationNode("computer_lab", "Computer Lab", ("computer laboratory", "cs lab")),
    LocationNode("library", "Library", ()),
    LocationNode(
        "engineering_building", "Engineering Building", ("engineering", "eng building")
    ),
    LocationNode(
        "student_affairs", "Student Affairs Office", ("student affairs", "registrar")
    ),
    LocationNode(
        "main_auditorium", "Main Auditorium", ("auditorium", "main hall")
    ),
    LocationNode("innovation_lab", "Innovation Lab", ("innovation laboratory",)),
    LocationNode("lecture_rooms", "Lecture Rooms", ("lecture hall", "classrooms")),
    LocationNode("cafeteria", "Cafeteria", ("cafe", "dining hall")),
    LocationNode("storage_room", "Storage Room", ("storage", "supply room")),
]

_EDGES: List[Tuple[LocationId, LocationId, float]] = [
    ("entrance", "main_hallway", 10),
    ("main_hallway", "ai_lab", 15),
    ("main_hallway", "robotics_lab", 20),
    ("main_hallway", "computer_lab", 12),
    ("main_hallway", "library", 25),
    ("main_hallway", "engineering_building", 8),
    ("main_hallway", "cafeteria", 18),
    ("main_hallway", "main_auditorium", 30),
    ("engineering_building", "student_affairs", 14),
    ("engineering_building", "innovation_lab", 22),
    ("library", "lecture_rooms", 10),
    ("robotics_lab", "innovation_lab", 16),
]

DEFAULT_MAP = NavigationMap(nodes=_NODES, edges=_EDGES)
