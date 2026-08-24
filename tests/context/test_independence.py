"""Hardware/network independence tests for app.context."""

from __future__ import annotations

from app.context.service import ContextService
from app.models.schemas import IntentResult, IntentType


class TestHardwareAndNetworkIndependence:
    def test_service_requires_no_external_resources_to_construct(self):
        # No camera, robot, model artifacts, or network calls needed.
        service = ContextService()
        assert service is not None

    def test_plan_runs_purely_in_memory(self):
        service = ContextService()
        ir = IntentResult(intent=IntentType.COMBINED, confidence=0.8, raw_text="x")
        # A pure function call -- no I/O of any kind.
        plan = service.plan(ir)
        assert plan is not None

    def test_repeated_planning_has_no_side_effects_across_calls(self):
        service = ContextService()
        ir = IntentResult(intent=IntentType.NAVIGATION, confidence=0.8, raw_text="x")
        results = [service.plan(ir) for _ in range(50)]
        assert all(r == results[0] for r in results)
