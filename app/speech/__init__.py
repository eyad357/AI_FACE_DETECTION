"""
Speech & Conversation layer (Person 2 — Speech / Conversation).

Responsibility: given a student's free-text utterance (plus optional
caller-provided context/intent/content), produce a language-appropriate
TEXT reply and an updated conversation context. This module performs
no speech synthesis and controls no hardware.

This package MUST NOT import app.robot, app.ml, app.vision, app.dl, or
app.main. It MAY use shared contracts from app.models (IntentType), the
same way app.ml.service does, so that a caller who already ran ML
intent classification can hand the result in. See
tests/speech/test_isolation.py for the enforced dependency rules and
docs/integration_contract.md for the full picture.
"""

from app.speech.context import ConversationContext
from app.speech.conversation import ConversationInput, ConversationService
from app.speech.language import Language
from app.speech.response import ConversationResponse, ConversationResponseType

__all__ = [
    "ConversationContext",
    "ConversationInput",
    "ConversationResponse",
    "ConversationResponseType",
    "ConversationService",
    "Language",
]
