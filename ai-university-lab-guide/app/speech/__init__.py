"""
Speech & Conversation layer (Person 2 — Robotics / Interaction).

Responsibility: given a student's free-text utterance, produce a
single, language-appropriate TEXT reply (ConversationResponse) plus an
updated ConversationContext. This module performs no speech synthesis
itself and has no notion of a Robot command — spoken_text is plain
text for a future orchestration layer to hand to
app.robot.RobotController.speak() / RobotCommand(SPEAK, ...).

This package MUST NOT import app.robot, app.ml, app.vision, app.dl,
or app.main. See tests/speech/test_isolation.py for the enforced
dependency rules.

Public API (re-exported here for convenience, per each submodule's own
usage examples):

    from app.speech import ConversationInput, ConversationService

    service = ConversationService()
    response = service.handle(ConversationInput(text="Where is the AI Lab?"))
    print(response.spoken_text)
"""

from app.speech.context import ConversationContext
from app.speech.conversation import ConversationInput, ConversationService
from app.speech.intent import IntentType
from app.speech.language import Language, PhraseKey
from app.speech.response import ConversationResponse, ConversationResponseType

__all__ = [
    "ConversationContext",
    "ConversationInput",
    "ConversationService",
    "ConversationResponse",
    "ConversationResponseType",
    "IntentType",
    "Language",
    "PhraseKey",
]
