"""Tests for the RequestPlan and CombinedResponse contracts (app.models.schemas)."""

from __future__ import annotations

import pytest

from app.models.schemas import Capability, CombinedResponse, IntentType, RequestPlan
from app.navigation.contracts import RouteFailureReason, RouteResult, RouteStep, RouteStepAction

# CombinedResponse.navigation_result is deliberately untyped/opaque in
# app.models.schemas (app.context/app.models must not import
# app.navigation -- see CombinedResponse's own docstring). These tests
# exercise it with the REAL Navigation contract
# (app.navigation.contracts.RouteResult), which is what a future
# orchestration layer will actually place there, rather than with the
# stale, never-produced NavigationResult dataclass that previously
# lived in app.models.schemas and has since been removed.


class TestRequestPlanContract:
    def test_valid_supported_plan(self):
        plan = RequestPlan(
            intent=IntentType.NAVIGATION,
            required_capabilities=(Capability.NAVIGATION,),
            supported=True,
        )
        assert plan.intent == IntentType.NAVIGATION
        assert plan.required_capabilities == (Capability.NAVIGATION,)

    def test_valid_unsupported_plan_requires_reason(self):
        with pytest.raises(ValueError):
            RequestPlan(intent=IntentType.UNKNOWN, supported=False, reason=None)

    def test_unsupported_plan_with_reason_is_valid(self):
        plan = RequestPlan(intent=IntentType.UNKNOWN, supported=False, reason="why")
        assert plan.supported is False
        assert plan.reason == "why"

    def test_rejects_bad_intent_type(self):
        with pytest.raises(ValueError):
            RequestPlan(intent="NAVIGATION")  # type: ignore[arg-type]

    def test_rejects_non_capability_in_tuple(self):
        with pytest.raises(ValueError):
            RequestPlan(
                intent=IntentType.NAVIGATION,
                required_capabilities=("NAVIGATION",),  # type: ignore[arg-type]
            )

    def test_rejects_list_instead_of_tuple(self):
        with pytest.raises(ValueError):
            RequestPlan(
                intent=IntentType.NAVIGATION,
                required_capabilities=[Capability.NAVIGATION],  # type: ignore[arg-type]
            )

    def test_is_frozen(self):
        plan = RequestPlan(intent=IntentType.HELP)
        with pytest.raises(Exception):
            plan.supported = False  # type: ignore[misc]

    def test_default_required_capabilities_is_empty(self):
        plan = RequestPlan(intent=IntentType.HELP)
        assert plan.required_capabilities == ()


class TestCombinedResponseContract:
    def test_defaults_to_both_none(self):
        response = CombinedResponse()
        assert response.navigation_result is None
        assert response.guide_response is None

    def test_navigation_only(self):
        step = RouteStep(
            sequence=1,
            from_location="A",
            to_location="B",
            action=RouteStepAction.ARRIVE,
            distance=5.0,
        )
        nav = RouteResult(
            success=True, origin="A", destination="B", steps=[step], total_distance=5.0
        )
        response = CombinedResponse(navigation_result=nav)
        assert response.navigation_result is nav
        assert response.guide_response is None

    def test_guide_response_is_opaque_and_untyped(self):
        # Deliberately untyped: app.context cannot import the real
        # app.guide.GuideResponse, so any object is accepted here.
        sentinel = object()
        response = CombinedResponse(guide_response=sentinel)
        assert response.guide_response is sentinel

    def test_navigation_result_is_opaque_and_untyped(self):
        # Deliberately untyped for the same reason as guide_response:
        # app.models must not import app.navigation. Any object is
        # accepted here -- CombinedResponse itself performs no
        # navigation-specific validation.
        sentinel = object()
        response = CombinedResponse(navigation_result=sentinel)
        assert response.navigation_result is sentinel

    def test_partial_failure_does_not_discard_success(self):
        # Navigation succeeds, Guide branch was never attempted/failed
        # (represented as None) -- the successful side must survive.
        step = RouteStep(
            sequence=1,
            from_location="A",
            to_location="B",
            action=RouteStepAction.ARRIVE,
            distance=5.0,
        )
        nav = RouteResult(
            success=True, origin="A", destination="B", steps=[step], total_distance=5.0
        )
        response = CombinedResponse(navigation_result=nav, guide_response=None)
        assert response.navigation_result.success is True
        assert response.guide_response is None

    def test_navigation_failure_is_representable_via_real_route_result(self):
        failed_nav = RouteResult(
            success=False,
            origin="A",
            destination="X",
            failure_reason=RouteFailureReason.UNREACHABLE,
            message="unreachable",
        )
        response = CombinedResponse(navigation_result=failed_nav)
        assert response.navigation_result.success is False
        assert response.navigation_result.message == "unreachable"

    def test_is_frozen(self):
        response = CombinedResponse()
        with pytest.raises(Exception):
            response.guide_response = object()  # type: ignore[misc]
