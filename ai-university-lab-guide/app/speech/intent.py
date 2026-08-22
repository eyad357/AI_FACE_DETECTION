"""
Conversational intent contract for the Speech & Conversation layer.

This module previously assumed a shared `IntentType` already existed
at `app.models.schemas.IntentType`. It does not: `app.models.schemas`
currently defines only `BoundingBox`, `FaceDetection`, and
`DetectionResult` (Vision's Phase 1 contracts), and `app.ml` — the
future module that would eventually classify a student's free-text
question into an intent (see app/ml/__init__.py's "Planned intents:
INFORMATION, NAVIGATION, COMBINED, HELP, UNKNOWN") — is still an
unimplemented placeholder with no public contract of its own.

`IntentType` is therefore, for now, a new, additive, Speech-owned
contract, following the same precedent already established by
`DecisionEvent` (app.decision.event_manager), `GuideResponse`
(app.guide.guide_service), and `ConversationResponse`
(app.speech.response): per docs/contracts.md's "Communication
philosophy", a contract only needs one canonical definition — it does
not have to live in app.models just because it may eventually cross a
module boundary, and it does not have to wait for the module on the
other side of that future boundary to exist first.

The five members below intentionally match app/ml/__init__.py's
already-documented "Planned intents" list exactly, so that if/when
app.ml is implemented, adopting a genuinely shared IntentType (whether
that ends up living in app.models or being re-exported from here) is a
same-values, no-surprises change — not a redesign. Speech does not
import app.ml, and app.ml importing this module (rather than the
reverse) would be the compatible direction if a shared type is wanted
later; that decision is deliberately deferred rather than made here.

Speech remains fully independently usable today: nothing in this
module requires app.ml to exist, and ConversationService computes its
own IntentType locally from the student's text (see
app.speech.conversation) without depending on any external classifier.
A caller who already has an intent from elsewhere may still pass an
IntentType into ConversationInput — see app.speech.conversation.
"""

from __future__ import annotations

from enum import Enum


class IntentType(Enum):
    """
    A student utterance's classified intent.

    Members mirror app/ml/__init__.py's planned intent set exactly:
        INFORMATION — the student is asking about a topic/location.
        NAVIGATION  — the student wants to be guided somewhere.
        COMBINED    — both information and navigation in one utterance.
        HELP        — the student is asking what the system can do.
        UNKNOWN     — no confident intent could be determined.
    """

    INFORMATION = "INFORMATION"
    NAVIGATION = "NAVIGATION"
    COMBINED = "COMBINED"
    HELP = "HELP"
    UNKNOWN = "UNKNOWN"
