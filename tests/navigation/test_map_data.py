"""Tests for app.navigation.map_data."""

from __future__ import annotations

import pytest

from app.navigation.map_data import DEFAULT_MAP, LocationNode, NavigationMap


class TestDefaultMapIntegrity:
    def test_known_locations_present(self):
        ids = DEFAULT_MAP.all_location_ids()
        for expected in ("entrance", "ai_lab", "robotics_lab", "library"):
            assert expected in ids

    def test_storage_room_is_known_but_isolated(self):
        assert DEFAULT_MAP.has_location("storage_room")
        assert DEFAULT_MAP.neighbors("storage_room") == {}

    def test_canonical_id_resolves_to_itself(self):
        assert DEFAULT_MAP.resolve("ai_lab") == "ai_lab"

    def test_display_name_resolves(self):
        assert DEFAULT_MAP.resolve("AI Lab") == "ai_lab"

    def test_alias_resolves_case_insensitively(self):
        assert DEFAULT_MAP.resolve("Artificial Intelligence Lab") == "ai_lab"
        assert DEFAULT_MAP.resolve("artificial intelligence lab") == "ai_lab"

    def test_unknown_name_returns_none(self):
        assert DEFAULT_MAP.resolve("mars base") is None

    def test_empty_or_none_resolves_to_none(self):
        assert DEFAULT_MAP.resolve("") is None

    def test_neighbors_are_symmetric(self):
        for location_id in DEFAULT_MAP.all_location_ids():
            for neighbor_id, distance in DEFAULT_MAP.neighbors(location_id).items():
                assert location_id in DEFAULT_MAP.neighbors(neighbor_id)
                assert DEFAULT_MAP.neighbors(neighbor_id)[location_id] == distance

    def test_neighbors_unknown_location_raises(self):
        with pytest.raises(KeyError):
            DEFAULT_MAP.neighbors("mars_base")


class TestNavigationMapConstruction:
    def test_duplicate_location_id_rejected(self):
        with pytest.raises(ValueError):
            NavigationMap(
                nodes=[LocationNode("a", "A"), LocationNode("a", "A2")],
                edges=[],
            )

    def test_edge_to_unknown_location_rejected(self):
        with pytest.raises(ValueError):
            NavigationMap(
                nodes=[LocationNode("a", "A")],
                edges=[("a", "b", 5)],
            )

    def test_self_loop_rejected(self):
        with pytest.raises(ValueError):
            NavigationMap(
                nodes=[LocationNode("a", "A")],
                edges=[("a", "a", 5)],
            )

    def test_non_positive_distance_rejected(self):
        with pytest.raises(ValueError):
            NavigationMap(
                nodes=[LocationNode("a", "A"), LocationNode("b", "B")],
                edges=[("a", "b", 0)],
            )
        with pytest.raises(ValueError):
            NavigationMap(
                nodes=[LocationNode("a", "A"), LocationNode("b", "B")],
                edges=[("a", "b", -5)],
            )

    def test_duplicate_edge_rejected(self):
        with pytest.raises(ValueError):
            NavigationMap(
                nodes=[LocationNode("a", "A"), LocationNode("b", "B")],
                edges=[("a", "b", 5), ("b", "a", 3)],
            )

    def test_ambiguous_alias_rejected(self):
        with pytest.raises(ValueError):
            NavigationMap(
                nodes=[
                    LocationNode("a", "A", ("shared",)),
                    LocationNode("b", "B", ("shared",)),
                ],
                edges=[],
            )

    def test_isolated_node_has_no_neighbors(self):
        nav_map = NavigationMap(nodes=[LocationNode("a", "A")], edges=[])
        assert nav_map.neighbors("a") == {}

    def test_get_node_returns_none_for_unknown(self):
        assert DEFAULT_MAP.get_node("mars_base") is None

    def test_get_node_returns_node_for_known(self):
        node = DEFAULT_MAP.get_node("ai_lab")
        assert node is not None
        assert node.name == "AI Lab"
