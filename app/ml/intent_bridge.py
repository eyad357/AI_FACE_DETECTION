"""
Intent translation boundary — Person 1 (ML) side only.

Context
-------
`app.models.schemas.IntentType` (ML's contract) and
`app.speech.intent.IntentType` (Speech's contract, Person 2) currently
define the same five members with the same string values:

    INFORMATION, NAVIGATION, COMBINED, HELP, UNKNOWN

They are, however, two distinct `enum.Enum` classes. A
`schemas.IntentType.NAVIGATION` member is never `==` to a
`speech.intent.IntentType.NAVIGATION` member, and neither passes an
`isinstance` check against the other's class, even though their names
and values are identical today.

This module does NOT resolve that duplication by importing
`app.speech` from ML, and it does NOT ask Speech to import `app.ml` --
either direction would violate both modules' existing, tested
dependency-isolation rules (see `docs/ml.md` and
`tests/speech/test_isolation.py`), and one Enum class cannot simply be
reassigned to equal another without breaking `isinstance` checks
already relied upon elsewhere (e.g. `IntentResult.__post_init__`,
`ContextService.plan()`).

What this module provides instead
----------------------------------
A single, generic, name-based conversion helper that a FUTURE
orchestration layer (not built in this phase -- see app.main's own
"only main.py connects modules" rule) can call to translate an ML
`IntentResult` into *any* structurally-compatible target Enum -- e.g.
Speech's `IntentType` -- without this module ever importing that
target Enum's defining module:

    from app.ml.service import MLIntentService
    from app.ml.intent_bridge import translate_intent
    from app.speech.intent import IntentType as SpeechIntentType

    ml = MLIntentService()
    result = ml.predict(student_text)
    speech_intent = translate_intent(result, SpeechIntentType)

The target Enum class is passed in BY THE CALLER at call time (the
orchestrator, which is allowed to import both sides). This module
itself has no import of, or reference to, `app.speech` anywhere --
confirmed by `tests/ml/test_intent_bridge.py`, which exercises this
function against a local dummy Enum with matching member names, not
against `app.speech.intent.IntentType` directly, so this module's own
test suite cannot accidentally introduce the very coupling it exists
to avoid.

Why a name-based mapping is safe here
--------------------------------------
`schemas.IntentType` and `speech.intent.IntentType` were designed
against the same documented vocabulary (see
`app/speech/intent.py`'s own docstring, which explicitly describes its
five members as mirroring ML's planned intent set "exactly, so that
if/when app.ml is implemented, adopting a genuinely shared IntentType
... is a same-values, no-surprises change"). Mapping by `.name` (not
`.value`, though today they are identical) is therefore a faithful,
lossless translation as long as both sides keep the same five member
names -- which is exactly the kind of drift `translate_intent`'s
`KeyError` (see below) is designed to catch loudly rather than
silently miscategorizing a request.

This module has no dependency on app.vision, app.robot, app.decision,
app.guide, app.navigation, app.dl, app.ui, app.speech, app.integration,
or app.main. It depends only on the Python standard library and
`app.models.schemas` (for the `IntentResult` type hint).
"""

from __future__ import annotations

from enum import Enum
from typing import Type, TypeVar

from app.models.schemas import IntentResult

_TargetEnum = TypeVar("_TargetEnum", bound=Enum)

__all__ = ["translate_intent", "IntentTranslationError"]


class IntentTranslationError(ValueError):
    """
    Raised when `translate_intent`'s source intent has no matching
    member (by name) in the caller-supplied target Enum.

    This should not happen for a target Enum that mirrors ML's
    documented five-member vocabulary (INFORMATION, NAVIGATION,
    COMBINED, HELP, UNKNOWN); if it does, the two vocabularies have
    drifted apart and that drift must be resolved explicitly rather
    than papered over with a silent fallback.
    """


def translate_intent(
    intent_result: IntentResult, target_enum: Type[_TargetEnum]
) -> _TargetEnum:
    """
    Translate an ML `IntentResult.intent` into the equivalent member of
    a caller-supplied target Enum, by member name.

    This function never imports the target Enum's defining module --
    the caller (a future orchestrator, not ML) supplies `target_enum`
    directly, so this module never depends on `app.speech` or any
    other Person 2 module.

    Args:
        intent_result: An `IntentResult` produced by
            `app.ml.service.MLIntentService.predict()`.
        target_enum: The Enum class to translate into (e.g. Speech's
            `app.speech.intent.IntentType`, or any Enum whose member
            names cover ML's vocabulary).

    Returns:
        The `target_enum` member whose `.name` matches
        `intent_result.intent.name`.

    Raises:
        TypeError: if `intent_result` is not an `IntentResult`.
        IntentTranslationError: if `target_enum` has no member whose
            name matches `intent_result.intent.name`.
    """
    if not isinstance(intent_result, IntentResult):
        raise TypeError(
            "translate_intent() requires an IntentResult, got "
            f"{type(intent_result).__name__}"
        )

    source_name = intent_result.intent.name
    try:
        return target_enum[source_name]
    except KeyError as exc:
        raise IntentTranslationError(
            f"{target_enum.__name__!r} has no member named {source_name!r} "
            f"(from ML IntentType {intent_result.intent!r}); the two "
            "intent vocabularies have diverged and this must be "
            "resolved explicitly, not silently."
        ) from exc
