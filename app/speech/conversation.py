"""
Conversation service — public entry point for the Speech & Conversation
layer.

Responsibility: given a student's free-text utterance (plus optional
caller-provided context/intent/content), produce a single
ConversationResponse containing a language-appropriate TEXT reply and
an updated ConversationContext.

Usage:

    from app.speech import ConversationInput, ConversationService

    service = ConversationService()
    response = service.handle(ConversationInput(text="Where is the AI Lab?"))
    print(response.spoken_text)

    # Continue the conversation, passing the updated context back in:
    follow_up = service.handle(ConversationInput(
        text="Can you guide me there?",
        context=response.context,
    ))
    print(follow_up.spoken_text)  # "Sure. I'll guide you to AI Lab."

Dependency rules (enforced — see tests/speech/test_isolation.py and
app/speech/__init__.py):
    This module MUST NOT import app.robot, app.ml, app.vision, app.dl,
    or app.main. It MAY use shared contracts from app.models
    (IntentType), the same way app.ml.service does, so that a caller
    who already ran ML intent classification can hand the result in
    without this module ever importing app.ml itself.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from app.models.schemas import IntentType
from app.speech.context import ConversationContext
from app.speech.knowledge import lookup_placeholder_information
from app.speech.language import Language, PhraseKey, detect_language, phrase
from app.speech.response import ConversationResponse, ConversationResponseType
from app.utils.logger import get_logger

logger = get_logger(__name__)

__all__ = ["ConversationInput", "ConversationService"]


@dataclass(frozen=True)
class ConversationInput:
    """
    Input contract for a single conversational turn.

    This is Speech's own input contract (no equivalent shared model
    existed for a free-text conversational turn). It intentionally
    lives here rather than app.models.schemas for the same reason
    ConversationResponse does — see response.py's docstring.

    Attributes:
        text: The student's raw utterance. May be malformed (None,
            non-str, empty, or whitespace-only) — handle() never
            raises for that, it returns a graceful clarification
            response instead.
        language: Optional explicit language override. When omitted,
            the service detects Arabic-script text automatically and
            otherwise continues in the conversation's existing
            language (see context.language).
        intent: Optional pre-classified intent, e.g. already produced
            by a caller via app.ml.service.MLIntentService.predict()
            (this module never imports app.ml itself — see the ML
            ISOLATION rules in app/speech/__init__.py). When omitted,
            a small local, non-ML, keyword-based heuristic is used
            instead so this module remains independently usable.
        context: The conversation's state from the previous turn. Omit
            (or pass None) to start a brand-new conversation.
        information_text: Optional caller-supplied content to speak
            for an INFORMATION-intent turn (e.g. already produced by
            app.guide.guide_service.GuideService.get_topic_content(...)
            .spoken_text). Always takes precedence over this module's
            own placeholder knowledge (app.speech.knowledge).
        destination: Optional caller-supplied destination/topic name,
            taking precedence over this module's own text extraction.
    """

    text: str
    language: Optional[Language] = None
    intent: Optional[IntentType] = None
    context: Optional[ConversationContext] = None
    information_text: Optional[str] = None
    destination: Optional[str] = None


# ---------------------------------------------------------------------------
# Local, deterministic, NON-ML intent inference
# ---------------------------------------------------------------------------
# Used only when the caller does not supply ConversationInput.intent.
# This is plain keyword/substring matching -- not a statistical model,
# not trained on data, and not app.ml. See "ML ISOLATION" in
# app/speech/__init__.py.

_FILLER_PREFIXES = (
    r"^can you\s+",
    r"^could you\s+",
    r"^would you\s+",
    r"^please\s+",
    r"^i want to\s+",
    r"^i would like to\s+",
    r"^i'd like to\s+",
)

_GREETING_WORDS = {
    "hello", "hi", "hey", "greetings",
    "good morning", "good afternoon", "good evening",
    "مرحبا", "مرحباً", "اهلا", "أهلا", "السلام عليكم",
}
_RESET_PHRASES = {
    "start over", "reset", "restart", "clear context",
    "من جديد", "إعادة", "ابدأ من جديد",
}
_YES_WORDS = {"yes", "yeah", "yep", "yup", "sure", "ok", "okay", "نعم", "أكيد", "تمام"}
_NO_WORDS = {"no", "nope", "nah", "لا", "كلا"}
_NAVIGATION_KEYWORDS = {
    "guide", "navigate", "take me", "route", "direction", "way to",
    "خذني", "دلني", "وجهني", "أرشدني", "الطريق",
}
_INFORMATION_KEYWORDS = {
    "where is", "where's", "wheres", "what is", "what's", "whats",
    "tell me about", "information about", "info about",
    "اين", "أين", "ما هو", "معلومات عن",
}
_HELP_KEYWORDS = {
    "help", "assist", "what can you do",
    "مساعدة", "ساعدني", "ماذا يمكنك ان تفعل",
}

_PRONOUN_REFERENTS = {"there", "it", "that", "that place", "here", "هناك"}


def _strip_filler_prefix(text: str) -> str:
    """Strip common leading filler ('can you', 'please', ...) so
    downstream keyword/entity matching sees the core request."""
    result = text.strip()
    changed = True
    while changed:
        changed = False
        for pattern in _FILLER_PREFIXES:
            updated = re.sub(pattern, "", result, flags=re.IGNORECASE)
            if updated != result:
                result = updated.strip()
                changed = True
    return result


def _infer_local_intent(text: str) -> str:
    """
    Deterministic, offline, keyword-based intent guess. Returns one of:
    "GREETING", "RESET", "CONFIRM_YES", "CONFIRM_NO", "NAVIGATION",
    "INFORMATION", "HELP", "UNKNOWN".
    """
    normalized = _strip_filler_prefix(text).lower().strip(" \t\n?!.")

    if not normalized:
        return "UNKNOWN"

    if any(normalized == w or normalized.startswith(w) for w in _GREETING_WORDS):
        return "GREETING"

    if any(phrase_ in normalized for phrase_ in _RESET_PHRASES):
        return "RESET"

    # Only treat a short, standalone message as a yes/no confirmation
    # -- avoids misreading "no" inside a longer sentence.
    word_count = len(normalized.split())
    if word_count <= 3:
        if normalized in _YES_WORDS:
            return "CONFIRM_YES"
        if normalized in _NO_WORDS:
            return "CONFIRM_NO"

    if any(keyword in normalized for keyword in _NAVIGATION_KEYWORDS):
        return "NAVIGATION"

    if any(keyword in normalized for keyword in _INFORMATION_KEYWORDS):
        return "INFORMATION"

    if any(keyword in normalized for keyword in _HELP_KEYWORDS):
        return "HELP"

    return "UNKNOWN"


_INTENT_TYPE_TO_LOCAL_LABEL = {
    IntentType.INFORMATION: "INFORMATION",
    IntentType.NAVIGATION: "NAVIGATION",
    # COMBINED requests both information and navigation; this phase
    # handles one intent per turn, so COMBINED is treated as
    # NAVIGATION-priority. Documented as a known limitation in
    # PHASE_REPORT.md -- a future orchestration phase may split a
    # COMBINED intent into two sequential Speech turns instead.
    IntentType.COMBINED: "NAVIGATION",
    IntentType.HELP: "HELP",
    IntentType.UNKNOWN: "UNKNOWN",
}

# ---------------------------------------------------------------------------
# Local, deterministic entity extraction (topic / destination names)
# ---------------------------------------------------------------------------

_INFO_LEAD_PATTERNS = (
    r"where is\s+",
    r"where's\s+",
    r"what is\s+",
    r"what's\s+",
    r"tell me about\s+",
    r"information about\s+",
    r"info about\s+",
)

_NAV_LEAD_PATTERNS = (
    r"guide me to\s+",
    r"take me to\s+",
    r"navigate to\s+",
    r"direct me to\s+",
    r"show me the way to\s+",
    r"go to\s+",
    r"guide me\s+",
    r"take me\s+",
)

_ARTICLE = r"(?:the |a |an )?"


def _extract_entity(text: str, lead_patterns) -> Optional[str]:
    stripped = _strip_filler_prefix(text)
    for lead in lead_patterns:
        pattern = rf"^{lead}{_ARTICLE}(.+?)[\s\?\.!]*$"
        match = re.match(pattern, stripped, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            if candidate:
                return candidate
    return None


def _extract_topic(text: str) -> Optional[str]:
    return _extract_entity(text, _INFO_LEAD_PATTERNS)


def _extract_destination(text: str) -> Optional[str]:
    return _extract_entity(text, _NAV_LEAD_PATTERNS)


class ConversationService:
    """
    Public entry point for the Speech & Conversation layer.

    Stateless from the caller's perspective (like
    app.ml.service.MLIntentService) -- ConversationContext is threaded
    explicitly through ConversationInput/ConversationResponse rather
    than held as mutable instance state, keeping every call
    deterministic and independently testable.
    """

    def __init__(self) -> None:
        logger.info("Conversation service initialized")

    # -- public API ---------------------------------------------------

    def handle(self, conv_input: ConversationInput) -> ConversationResponse:
        """
        Process one conversational turn.

        Never raises for malformed input (None/non-str/empty text) --
        returns a graceful clarification-style response instead so a
        caller can safely call this in a loop without validating input
        first.
        """
        context = conv_input.context or ConversationContext.initial()
        text = conv_input.text

        if not isinstance(text, str) or not text.strip():
            logger.warning("ConversationService.handle called with malformed input")
            language = conv_input.language or context.language
            new_context = context.with_updates(
                turn_count=context.turn_count + 1,
                last_user_text=text if isinstance(text, str) else None,
                last_intent="MALFORMED_INPUT",
            )
            return self._respond(
                key=PhraseKey.MALFORMED_INPUT,
                response_type=ConversationResponseType.MALFORMED_INPUT,
                language=language,
                context=new_context,
                requires_clarification=True,
            )

        language = self._resolve_language(conv_input, context, text)

        # A pending clarification takes priority: the student's reply
        # is treated as the direct answer to what we asked, not
        # re-classified as a fresh intent.
        if context.pending_clarification == "destination":
            return self._handle_destination_answer(conv_input, context, language, text)
        if context.pending_clarification == "topic":
            return self._handle_topic_answer(conv_input, context, language, text)

        intent_label = self._resolve_intent(conv_input, text)
        logger.info("Conversation turn intent resolved as %s", intent_label)

        handler = {
            "GREETING": self._handle_greeting,
            "RESET": self._handle_reset,
            "HELP": self._handle_help,
            "NAVIGATION": self._handle_navigation,
            "INFORMATION": self._handle_information,
            "CONFIRM_YES": self._handle_confirm_yes,
            "CONFIRM_NO": self._handle_confirm_no,
        }.get(intent_label, self._handle_unknown)

        return handler(conv_input, context, language, text)

    def greet(self, context: Optional[ConversationContext] = None,
              language: Optional[Language] = None) -> ConversationResponse:
        """Convenience helper to produce an opening greeting turn."""
        base_context = context or ConversationContext.initial(language=language)
        return self.handle(ConversationInput(text="hello", language=language, context=base_context))

    def reset(self, context: Optional[ConversationContext] = None) -> ConversationContext:
        """Return a brand-new context, preserving language when known."""
        base_context = context or ConversationContext.initial()
        return base_context.reset()

    # -- intent/language resolution -----------------------------------

    @staticmethod
    def _resolve_language(conv_input: ConversationInput,
                           context: ConversationContext, text: str) -> Language:
        if conv_input.language is not None:
            return conv_input.language
        detected = detect_language(text)
        if detected != Language.default():
            return detected
        return context.language or Language.default()

    @staticmethod
    def _resolve_intent(conv_input: ConversationInput, text: str) -> str:
        if conv_input.intent is not None:
            return _INTENT_TYPE_TO_LOCAL_LABEL.get(conv_input.intent, "UNKNOWN")
        return _infer_local_intent(text)

    # -- turn handlers ---------------------------------------------------

    def _handle_greeting(self, conv_input, context, language, text):
        new_context = self._advance_context(context, language, text, "GREETING")
        return self._respond(PhraseKey.GREETING, ConversationResponseType.GREETING,
                              language, new_context)

    def _handle_reset(self, conv_input, context, language, text):
        new_context = context.reset(keep_language=True).with_updates(
            turn_count=context.turn_count + 1,
            last_user_text=text,
            last_intent="RESET",
        )
        return self._respond(PhraseKey.CONTEXT_RESET, ConversationResponseType.CONTEXT_RESET,
                              language, new_context)

    def _handle_help(self, conv_input, context, language, text):
        new_context = self._advance_context(context, language, text, "HELP")
        return self._respond(PhraseKey.HELP, ConversationResponseType.HELP,
                              language, new_context)

    def _handle_confirm_yes(self, conv_input, context, language, text):
        new_context = self._advance_context(context, language, text, "CONFIRM_YES")
        return self._respond(PhraseKey.CONFIRMATION_ACK_YES,
                              ConversationResponseType.CONFIRMATION_ACK, language, new_context)

    def _handle_confirm_no(self, conv_input, context, language, text):
        new_context = self._advance_context(context, language, text, "CONFIRM_NO")
        return self._respond(PhraseKey.CONFIRMATION_ACK_NO,
                              ConversationResponseType.CONFIRMATION_ACK, language, new_context)

    def _handle_unknown(self, conv_input, context, language, text):
        new_context = self._advance_context(context, language, text, "UNKNOWN")
        return self._respond(PhraseKey.FALLBACK_UNKNOWN,
                              ConversationResponseType.FALLBACK_UNKNOWN, language, new_context)

    def _handle_navigation(self, conv_input, context, language, text):
        destination = conv_input.destination or _extract_destination(text)

        if destination and destination.lower() in _PRONOUN_REFERENTS:
            destination = None  # pronoun -- fall through to context lookup

        if not destination:
            destination = context.current_destination or context.current_topic

        if not destination:
            new_context = context.with_updates(
                turn_count=context.turn_count + 1,
                last_user_text=text,
                last_intent="NAVIGATION",
                pending_clarification="destination",
                language=language,
            )
            return self._respond(PhraseKey.NAVIGATION_CLARIFICATION,
                                  ConversationResponseType.CLARIFICATION, language,
                                  new_context, requires_clarification=True)

        new_context = context.with_updates(
            turn_count=context.turn_count + 1,
            last_user_text=text,
            last_intent="NAVIGATION",
            current_destination=destination,
            current_topic=context.current_topic or destination,
            pending_clarification=None,
            language=language,
        )
        return self._respond(PhraseKey.NAVIGATION_CONFIRMATION,
                              ConversationResponseType.NAVIGATION_CONFIRMATION,
                              language, new_context, destination=destination)

    def _handle_information(self, conv_input, context, language, text):
        topic = conv_input.destination or _extract_topic(text)

        if not topic:
            new_context = context.with_updates(
                turn_count=context.turn_count + 1,
                last_user_text=text,
                last_intent="INFORMATION",
                pending_clarification="topic",
                language=language,
            )
            return self._respond(PhraseKey.INFORMATION_CLARIFICATION,
                                  ConversationResponseType.CLARIFICATION, language,
                                  new_context, requires_clarification=True)

        info_text = conv_input.information_text or lookup_placeholder_information(topic)
        new_context = context.with_updates(
            turn_count=context.turn_count + 1,
            last_user_text=text,
            last_intent="INFORMATION",
            current_topic=topic,
            pending_clarification=None,
            language=language,
        )

        if info_text:
            return ConversationResponse(
                spoken_text=info_text,
                response_type=ConversationResponseType.INFORMATION,
                language=language,
                context=new_context,
            )

        return self._respond(PhraseKey.INFORMATION_UNKNOWN_TOPIC,
                              ConversationResponseType.INFORMATION, language, new_context)

    # -- clarification-answer handlers -----------------------------------

    def _handle_destination_answer(self, conv_input, context, language, text):
        destination = conv_input.destination or text.strip()
        new_context = context.with_updates(
            turn_count=context.turn_count + 1,
            last_user_text=text,
            last_intent="NAVIGATION",
            current_destination=destination,
            current_topic=context.current_topic or destination,
            pending_clarification=None,
            language=language,
        )
        return self._respond(PhraseKey.NAVIGATION_CONFIRMATION,
                              ConversationResponseType.NAVIGATION_CONFIRMATION,
                              language, new_context, destination=destination)

    def _handle_topic_answer(self, conv_input, context, language, text):
        topic = conv_input.destination or text.strip()
        info_text = conv_input.information_text or lookup_placeholder_information(topic)
        new_context = context.with_updates(
            turn_count=context.turn_count + 1,
            last_user_text=text,
            last_intent="INFORMATION",
            current_topic=topic,
            pending_clarification=None,
            language=language,
        )
        if info_text:
            return ConversationResponse(
                spoken_text=info_text,
                response_type=ConversationResponseType.INFORMATION,
                language=language,
                context=new_context,
            )
        return self._respond(PhraseKey.INFORMATION_UNKNOWN_TOPIC,
                              ConversationResponseType.INFORMATION, language, new_context)

    # -- helpers -----------------------------------------------------

    @staticmethod
    def _advance_context(context: ConversationContext, language: Language,
                          text: str, intent_label: str) -> ConversationContext:
        return context.with_updates(
            turn_count=context.turn_count + 1,
            last_user_text=text,
            last_intent=intent_label,
            language=language,
        )

    @staticmethod
    def _respond(key: PhraseKey, response_type: ConversationResponseType,
                 language: Language, context: ConversationContext,
                 requires_clarification: bool = False, **format_kwargs: str) -> ConversationResponse:
        text = phrase(key, language, **format_kwargs)
        return ConversationResponse(
            spoken_text=text,
            response_type=response_type,
            language=language,
            context=context,
            requires_clarification=requires_clarification,
        )
