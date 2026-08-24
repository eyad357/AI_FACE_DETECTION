"""Tests for app.navigation.pathfinder."""

from __future__ import annotations

import pytest

from app.navigation.map_data import DEFAULT_MAP, LocationNode, NavigationMap
from app.navigation.pathfinder import find_shortest_path


class TestBasicRoutes:
    def test_direct_neighbor_route(self):
        result = find_shortest_path(DEFAULT_MAP, "entrance", "main_hallway")
        assert result is not None
        assert result.location_ids == ["entrance", "main_hallway"]
        assert result.total_distance == 10

    def test_multi_step_route(self):
        result = find_shortest_path(DEFAULT_MAP, "entrance", "ai_lab")
        assert result is not None
        assert result.location_ids == ["entrance", "main_hallway", "ai_lab"]
        assert result.total_distance == 25

    def test_origin_equals_destination(self):
        result = find_shortest_path(DEFAULT_MAP, "ai_lab", "ai_lab")
        assert result is not None
        assert result.location_ids == ["ai_lab"]
        assert result.total_distance == 0


class TestShortestCostSelection:
    def test_picks_lowest_total_distance_not_fewest_hops(self):
        # entrance -> innovation_lab has two candidate paths:
        #   via engineering_building: 10 + 8 + 22 = 40  (3 hops)
        #   via robotics_lab:         10 + 20 + 16 = 46 (3 hops)
        # Both are 3 hops, so this specifically exercises weighted
        # selection, not hop-count.
        result = find_shortest_path(DEFAULT_MAP, "entrance", "innovation_lab")
        assert result is not None
        assert result.total_distance == 40
        assert result.location_ids == [
            "entrance",
            "main_hallway",
            "engineering_building",
            "innovation_lab",
        ]

    def test_custom_map_prefers_more_hops_lower_cost(self):
        # a -> c direct is expensive; a -> b -> c is cheaper despite
        # being an extra hop.
        nav_map = NavigationMap(
            nodes=[
                LocationNode("a", "A"),
                LocationNode("b", "B"),
                LocationNode("c", "C"),
            ],
            edges=[("a", "c", 100), ("a", "b", 10), ("b", "c", 10)],
        )
        result = find_shortest_path(nav_map, "a", "c")
        assert result is not None
        assert result.location_ids == ["a", "b", "c"]
        assert result.total_distance == 20


class TestUnreachableAndUnknown:
    def test_isolated_known_location_is_unreachable(self):
        result = find_shortest_path(DEFAULT_MAP, "entrance", "storage_room")
        assert result is None

    def test_unknown_origin_raises_key_error(self):
        with pytest.raises(KeyError):
            find_shortest_path(DEFAULT_MAP, "mars_base", "ai_lab")

    def test_unknown_destination_raises_key_error(self):
        with pytest.raises(KeyError):
            find_shortest_path(DEFAULT_MAP, "ai_lab", "mars_base")


class TestDeterminism:
    def test_repeated_calls_return_identical_result(self):
        first = find_shortest_path(DEFAULT_MAP, "entrance", "lecture_rooms")
        second = find_shortest_path(DEFAULT_MAP, "entrance", "lecture_rooms")
        assert first == second

    def test_deterministic_across_many_runs(self):
        results = {
            tuple(find_shortest_path(DEFAULT_MAP, "entrance", "cafeteria").location_ids)
            for _ in range(20)
        }
        assert len(results) == 1
