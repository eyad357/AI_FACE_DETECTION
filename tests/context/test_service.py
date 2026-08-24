"""Tests for app.context.service -- the public request-planning API."""

from __future__ import annotations

import pytest

from app.context.service import ContextService
from app.models.schemas import Capability, IntentResult, IntentType, RequestPlan


@pytest.fixture(scope="module")
def context() -> ContextService:
    return ContextService()


def _intent_result(intent: IntentType, text: str = "test question") -> IntentResult:
    return IntentResult(intent=intent, confidence=0.9, raw_text=text)


class TestSupportedIntentPlanning:
    def test_information_requires_guide(self, context):
        plan = context.plan(_intent_result(IntentType.INFORMATION))
        assert plan.required_capabilities == (Capability.GUIDE,)
        assert plan.supported is True

    def test_navigation_requires_navigation(self, context):
        plan = context.plan(_intent_result(IntentType.NAVIGATION))
        assert plan.required_capabilities == (Capability.NAVIGATION,)
        assert plan.supported is True

    def test_combined_requires_navigation_and_guide(self, context):
        plan = context.plan(_intent_result(IntentType.COMBINED))
        assert plan.required_capabilities == (Capability.NAVIGATION, Capability.GUIDE)
        assert plan.supported is True

    def test_help_requires_no_capabilities(self, context):
        plan = context.plan(_intent_result(IntentType.HELP))
        assert plan.required_capabilities == ()
        assert plan.supported is True
        assert plan.reason is not None


class TestUnsupportedIntentHandling:
    def test_unknown_is_unsupported(self, context):
        plan = context.plan(_intent_result(IntentType.UNKNOWN))
        assert plan.supported is False
        assert plan.required_capabilities == ()
        assert plan.reason is not None

    def test_unknown_does_not_raise(self, context):
        # Must be handled safely, not treated as an error.
        plan = context.plan(_intent_result(IntentType.UNKNOWN))
        assert isinstance(plan, RequestPlan)


class TestInvalidInputHandling:
    def test_non_intent_result_raises_type_error(self, context):
        with pytest.raises(TypeError):
            context.plan("Where is the AI Lab?")  # type: ignore[arg-type]

    def test_none_raises_type_error(self, context):
        with pytest.raises(TypeError):
            context.plan(None)  # type: ignore[arg-type]

    def test_plain_dict_raises_type_error(self, context):
        with pytest.raises(TypeError):
            context.plan({"intent": "NAVIGATION"})  # type: ignore[arg-type]


class TestRequestPlanContractReturned:
    def test_returns_request_plan_instance(self, context):
        plan = context.plan(_intent_result(IntentType.NAVIGATION))
        assert isinstance(plan, RequestPlan)

    def test_plan_carries_original_intent(self, context):
        plan = context.plan(_intent_result(IntentType.COMBINED))
        assert plan.intent == IntentType.COMBINED


class TestDeterminism:
    def test_same_intent_result_produces_equal_plan(self, context):
        ir = _intent_result(IntentType.COMBINED)
        first = context.plan(ir)
        second = context.plan(ir)
        assert first == second

    def test_confidence_and_raw_text_do_not_affect_plan(self, context):
        # Only .intent matters for planning -- confidence/raw_text are
        # ML's concern, not Context's.
        low_confidence = IntentResult(
            intent=IntentType.NAVIGATION, confidence=0.1, raw_text="a"
        )
        high_confidence = IntentResult(
            intent=IntentType.NAVIGATION, confidence=0.99, raw_text="completely different text"
        )
        assert context.plan(low_confidence) == context.plan(high_confidence)

    def test_new_service_instance_gives_same_result(self):
        ir = _intent_result(IntentType.INFORMATION)
        a = ContextService().plan(ir)
        b = ContextService().plan(ir)
        assert a == b


class TestNoRawTextClassification:
    def test_plan_ignores_raw_text_content_entirely(self, context):
        # Deliberately misleading raw_text: the plan must follow
        # .intent, never re-derive intent from the text itself.
        ir = IntentResult(
            intent=IntentType.HELP,
            confidence=0.9,
            raw_text="Where is the AI Lab and what is it used for?",
        )
        plan = context.plan(ir)
        assert plan.required_capabilities == ()  # HELP's plan, not COMBINED's


class TestPublicServiceAPI:
    def test_plan_is_the_only_public_entry_point(self):
        public_methods = [
            name
            for name in dir(ContextService)
            if not name.startswith("_") and callable(getattr(ContextService, name))
        ]
        assert public_methods == ["plan"]
