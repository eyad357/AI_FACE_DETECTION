"""
Context public API — request planning service.

Responsibility: given an already-classified IntentResult (produced by
app.ml), determine which capabilities are required to fulfill the
request. Nothing more.

Usage:

    from app.context.service import ContextService

    context = ContextService()
    plan = context.plan(intent_result)  # -> RequestPlan

Context does NOT classify text (that's app.ml's job), does NOT
calculate routes (app.navigation), does NOT look up information
(app.guide), and does NOT orchestrate the actual application (that
remains app.main's future job). It is a pure, deterministic mapping
from IntentResult to RequestPlan.

Dependency rules (enforced, see docs/context.md and
app/context/__init__.py):
    Context MUST NOT import app.ml, app.dl, app.vision, app.navigation,
    app.guide, app.robot, app.ui, or app.main.
    Context MAY use shared contracts from app.models.
"""

from __future__ import annotations

from app.models.schemas import Capability, IntentResult, IntentType, RequestPlan

__all__ = ["ContextService"]

# Deterministic intent -> required-capabilities mapping. Order within
# each tuple is stable (NAVIGATION before GUIDE for COMBINED) so
# RequestPlan output never varies between calls.
_CAPABILITY_MAP = {
    IntentType.INFORMATION: (Capability.GUIDE,),
    IntentType.NAVIGATION: (Capability.NAVIGATION,),
    IntentType.COMBINED: (Capability.NAVIGATION, Capability.GUIDE),
}

# HELP needs no capability module -- see IntentType's own docstring
# (app.ml): HELP means the student doesn't know what to ask, which is
# a self-contained response, not a Guide/Navigation data request.
_HELP_REASON = (
    "HELP requires no Navigation or Guide capability: per IntentType's "
    "existing semantics (app.ml), HELP means the student does not know "
    "what to ask, which calls for a self-contained guidance response "
    "rather than a data lookup."
)

# UNKNOWN has no defined plan -- see IntentType's own docstring
# (app.ml): UNKNOWN is ML's low-confidence/unclassifiable fallback.
_UNKNOWN_REASON = (
    "UNKNOWN has no defined request plan: per IntentType's existing "
    "semantics (app.ml), UNKNOWN means the intent could not be "
    "confidently classified, so no capability can be safely selected."
)


class ContextService:
    """
    Public entry point for request planning.

    Stateless: plan() is a pure function of its input, safe to call
    repeatedly and safe to share a single instance across requests.
    """

    def plan(self, intent_result: IntentResult) -> RequestPlan:
        """
        Determine the RequestPlan for a single classified request.

        Args:
            intent_result: The IntentResult produced by app.ml for one
                student question.

        Returns:
            A RequestPlan. For INFORMATION/NAVIGATION/COMBINED,
            supported=True with the corresponding capabilities (see
            module-level _CAPABILITY_MAP). For HELP, supported=True
            with no capabilities and a reason explaining why. For
            UNKNOWN (or any other value that isn't a recognized,
            planned intent), supported=False with no capabilities and
            a reason explaining why.

        Raises:
            TypeError: if intent_result is not an IntentResult. Context
                consumes only the existing IntentResult contract (see
                docs/context.md) -- it never classifies raw text itself.
        """
        if not isinstance(intent_result, IntentResult):
            raise TypeError(
                "ContextService.plan() requires an IntentResult, got "
                f"{type(intent_result).__name__}. Context consumes "
                "IntentResult only -- it does not classify raw text "
                "(that is app.ml's responsibility)."
            )

        intent = intent_result.intent

        if intent in _CAPABILITY_MAP:
            return RequestPlan(
                intent=intent,
                required_capabilities=_CAPABILITY_MAP[intent],
                supported=True,
            )

        if intent is IntentType.HELP:
            return RequestPlan(
                intent=intent,
                required_capabilities=(),
                supported=True,
                reason=_HELP_REASON,
            )

        # IntentType.UNKNOWN, or any future IntentType member this
        # mapping doesn't yet know about -- fail safe, never guess.
        reason = (
            _UNKNOWN_REASON
            if intent is IntentType.UNKNOWN
            else (
                f"{intent.name} has no defined request plan in app.context "
                "yet -- extend _CAPABILITY_MAP (see docs/context.md, "
                '"Extension guidelines") rather than guessing a capability set.'
            )
        )
        return RequestPlan(
            intent=intent,
            required_capabilities=(),
            supported=False,
            reason=reason,
        )
