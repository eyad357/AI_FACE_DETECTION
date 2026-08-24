"""Tests for app.navigation.service.NavigationService (the public API)."""

from __future__ import annotations

import pytest

from app.navigation.contracts import (
    RouteFailureReason,
    RouteRequest,
    RouteResult,
    RouteStep,
    RouteStepAction,
)
from app.navigation.map_data import DEFAULT_MAP, LocationNode, NavigationMap
from app.navigation.service import NavigationService


@pytest.fixture
def nav() -> NavigationService:
    return NavigationService()


class TestBasicRouting:
    def test_basic_route_success(self, nav):
        result = nav.find_route(RouteRequest(origin="entrance", destination="ai_lab"))
        assert result.success is True
        assert result.failure_reason is None
        assert result.total_distance == 25
        assert [s.to_location for s in result.steps] == ["main_hallway", "ai_lab"]

    def test_multi_step_route_has_ordered_sequence_numbers(self, nav):
        result = nav.find_route(
            RouteRequest(origin="entrance", destination="innovation_lab")
        )
        assert result.success is True
        assert [s.sequence for s in result.steps] == list(
            range(1, len(result.steps) + 1)
        )

    def test_shortest_cost_route_chosen(self, nav):
        result = nav.find_route(
            RouteRequest(origin="entrance", destination="innovation_lab")
        )
        assert result.total_distance == 40

    def test_last_step_action_is_arrive(self, nav):
        result = nav.find_route(RouteRequest(origin="entrance", destination="ai_lab"))
        assert result.steps[-1].action == RouteStepAction.ARRIVE

    def test_first_step_action_is_depart(self, nav):
        result = nav.find_route(
            RouteRequest(origin="entrance", destination="innovation_lab")
        )
        assert result.steps[0].action == RouteStepAction.DEPART

    def test_route_accepts_aliases_and_display_names(self, nav):
        result = nav.find_route(
            RouteRequest(origin="Main Entrance", destination="artificial intelligence lab")
        )
        assert result.success is True
        assert result.total_distance == 25


class TestFailureModes:
    def test_unknown_origin(self, nav):
        result = nav.find_route(RouteRequest(origin="mars_base", destination="ai_lab"))
        assert result.success is False
        assert result.failure_reason == RouteFailureReason.UNKNOWN_ORIGIN
        assert result.steps == []
        assert result.total_distance is None

    def test_unknown_destination(self, nav):
        result = nav.find_route(RouteRequest(origin="entrance", destination="mars_base"))
        assert result.success is False
        assert result.failure_reason == RouteFailureReason.UNKNOWN_DESTINATION

    def test_unreachable_destination(self, nav):
        result = nav.find_route(
            RouteRequest(origin="entrance", destination="storage_room")
        )
        assert result.success is False
        assert result.failure_reason == RouteFailureReason.UNREACHABLE

    def test_malformed_request_empty_origin(self, nav):
        result = nav.find_route(RouteRequest(origin="", destination="ai_lab"))
        assert result.success is False
        assert result.failure_reason == RouteFailureReason.INVALID_REQUEST

    def test_malformed_request_empty_destination(self, nav):
        result = nav.find_route(RouteRequest(origin="entrance", destination=""))
        assert result.success is False
        assert result.failure_reason == RouteFailureReason.INVALID_REQUEST

    def test_malformed_request_whitespace_only(self, nav):
        result = nav.find_route(RouteRequest(origin="   ", destination="ai_lab"))
        assert result.success is False
        assert result.failure_reason == RouteFailureReason.INVALID_REQUEST

    def test_failure_never_raises(self, nav):
        # None of the "expected" failure paths should raise.
        for request in (
            RouteRequest(origin="mars", destination="ai_lab"),
            RouteRequest(origin="entrance", destination="mars"),
            RouteRequest(origin="entrance", destination="storage_room"),
            RouteRequest(origin="", destination=""),
        ):
            nav.find_route(request)  # must not raise


class TestOriginEqualsDestination:
    def test_same_canonical_location(self, nav):
        result = nav.find_route(RouteRequest(origin="ai_lab", destination="ai_lab"))
        assert result.success is True
        assert result.steps == []
        assert result.total_distance == 0
        assert result.message is not None

    def test_same_location_via_alias_and_canonical_id(self, nav):
        result = nav.find_route(RouteRequest(origin="AI Lab", destination="ai_lab"))
        assert result.success is True
        assert result.steps == []
        assert result.total_distance == 0


class TestDeterminism:
    def test_repeated_calls_return_equal_result(self, nav):
        first = nav.find_route(RouteRequest(origin="entrance", destination="library"))
        second = nav.find_route(RouteRequest(origin="entrance", destination="library"))
        assert first == second


class TestDestinationResolution:
    def test_resolve_destination_known(self, nav):
        assert nav.resolve_destination("ai lab") == "ai_lab"

    def test_resolve_destination_unknown(self, nav):
        assert nav.resolve_destination("mars base") is None


class TestPublicApiContract:
    def test_find_route_returns_route_result(self, nav):
        result = nav.find_route(RouteRequest(origin="entrance", destination="ai_lab"))
        assert isinstance(result, RouteResult)

    def test_route_result_does_not_expose_internal_graph(self, nav):
        result = nav.find_route(RouteRequest(origin="entrance", destination="ai_lab"))
        # RouteResult must only ever surface RouteStep objects, never
        # NavigationMap/LocationNode/adjacency internals.
        for step in result.steps:
            assert isinstance(step, RouteStep)

    def test_custom_map_can_be_injected(self):
        tiny_map = NavigationMap(
            nodes=[LocationNode("x", "X"), LocationNode("y", "Y")],
            edges=[("x", "y", 7)],
        )
        service = NavigationService(nav_map=tiny_map)
        result = service.find_route(RouteRequest(origin="x", destination="y"))
        assert result.success is True
        assert result.total_distance == 7

    def test_default_service_uses_default_map(self, nav):
        result = nav.find_route(RouteRequest(origin="entrance", destination="ai_lab"))
        assert result.success is True
        # sanity: DEFAULT_MAP is what backs the default service
        assert DEFAULT_MAP.resolve("ai_lab") == "ai_lab"
