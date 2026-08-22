"""
Conversation response contract for the Speech & Conversation layer.

This is Speech's own output contract — no equivalent model existed
anywhere in the project for a TEXT-only dialogue response (Guide's
GuideResponse is topic *content*, not a conversational turn; it has no
notion of clarification, confirmation, or conversation context), so
this is a new, additive, Speech-owned contract. It intentionally lives
in app.speech rather than app.models.schemas — the same pattern
already used by DecisionEvent (app.decision.event_manager) and
GuideResponse (app.guide.guide_service), per docs/contracts.md's
"Communication philosophy" (a contract only needs one canonical
definition; it doesn't have to live in app.models just because it
crosses a module boundary).

ConversationResponse.spoken_text is TEXT ONLY. This module performs no
speech synthesis and has no notion of a Robot command — a future
orchestration layer may map `spoken_text` onto
`app.robot.RobotController.speak()` / `RobotCommand(SPEAK, ...)`, but
that mapping is out of scope for this phase (see app/speech/__init__.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from app.speech.context import ConversationContext
from app.speech.language import Language


class ConversationResponseType(Enum):
    """
    The kind of conversational turn a ConversationResponse represents.
    Purely descriptive/informational for callers (e.g. logging, UI) —
    app.speech itself never branches on another module's behavior
    based on this value.
    """

    GREETING = "GREETING"
    INFORMATION = "INFORMATION"
    NAVIGATION_CONFIRMATION = "NAVIGATION_CONFIRMATION"
    CLARIFICATION = "CLARIFICATION"
    CONFIRMATION_ACK = "CONFIRMATION_ACK"
    HELP = "HELP"
    FALLBACK_UNKNOWN = "FALLBACK_UNKNOWN"
    MALFORMED_INPUT = "MALFORMED_INPUT"
    CONTEXT_RESET = "CONTEXT_RESET"


@dataclass(frozen=True)
class ConversationResponse:
    """
    Canonical output of ConversationService.handle() for a single
    conversational turn.

    Attributes:
        spoken_text: Plain, language-appropriate text for a future
            orchestration layer to hand to Robot/UI. This module does
            not synthesize or play speech itself.
        response_type: What kind of turn this was.
        language: The language `spoken_text` is written in.
        context: The UPDATED ConversationContext after this turn —
            callers should pass this into the next ConversationInput
            to preserve context across turns.
        requires_clarification: True when the system is waiting on the
            student to clarify something (mirrors
            context.pending_clarification is not None, exposed
            directly so callers don't need to inspect context
            internals).
        timestamp: When this response was produced (UTC).
    """

    spoken_text: str
    response_type: ConversationResponseType
    language: Language
    context: ConversationContext
    requires_clarification: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
