"""
Tests for app.speech (ConversationService / ConversationInput /
ConversationResponse / ConversationContext).

These tests require no Robot, Robot SDK, camera, Vision, ML, database,
or network access. Every scenario uses only plain text input and
optional caller-provided context/intent -- no hardware, no external
services, fully deterministic.
"""

import pytest

from app.models.schemas import IntentType
from app.speech import (
    ConversationContext,
    ConversationInput,
    ConversationResponse,
    ConversationResponseType,
    ConversationService,
    Language,
)


@pytest.fixture()
def service() -> ConversationService:
    return ConversationService()


class TestInitialization:
    def test_initializes_without_error(self):
        ConversationService()  # should not raise

    def test_fresh_context_starts_at_turn_zero(self):
        context = ConversationContext.initial()
        assert context.turn_count == 0
        assert context.language is Language.ENGLISH
        assert context.pending_clarification is None


class TestGreeting:
    def test_hello_produces_greeting_response(self, service):
        response = service.handle(ConversationInput(text="Hello"))
        assert response.response_type is ConversationResponseType.GREETING
        assert response.spoken_text
        assert response.context.turn_count == 1
        assert response.context.last_intent == "GREETING"

    def test_greet_convenience_method(self, service):
        response = service.greet()
        assert response.response_type is ConversationResponseType.GREETING

    def test_arabic_greeting_word_detected(self, service):
        response = service.handle(ConversationInput(text="مرحبا"))
        assert response.response_type is ConversationResponseType.GREETING
        assert response.language is Language.ARABIC


class TestInformationResponse:
    def test_where_is_the_ai_lab(self, service):
        response = service.handle(ConversationInput(text="Where is the AI Lab?"))
        assert response.response_type is ConversationResponseType.INFORMATION
        assert "AI Lab" in response.spoken_text or "second floor" in response.spoken_text
        assert response.context.current_topic == "AI Lab"

    def test_caller_supplied_information_text_takes_precedence(self, service):
        response = service.handle(ConversationInput(
            text="Tell me about the Robotics Lab",
            information_text="Custom caller-provided content.",
        ))
        assert response.spoken_text == "Custom caller-provided content."
        assert response.response_type is ConversationResponseType.INFORMATION

    def test_unknown_topic_gives_controlled_response_not_crash(self, service):
        response = service.handle(ConversationInput(text="Tell me about the quantum reactor"))
        assert response.response_type is ConversationResponseType.INFORMATION
        assert response.spoken_text  # non-empty, controlled fallback text
        assert response.context.current_topic == "quantum reactor"


class TestNavigationConfirmation:
    def test_guide_me_to_the_library(self, service):
        response = service.handle(ConversationInput(text="Can you guide me to the library?"))
        assert response.response_type is ConversationResponseType.NAVIGATION_CONFIRMATION
        assert "library" in response.spoken_text.lower()
        assert response.context.current_destination == "library"

    def test_caller_supplied_destination_takes_precedence(self, service):
        response = service.handle(ConversationInput(
            text="Take me there", destination="Main Gate",
        ))
        assert response.response_type is ConversationResponseType.NAVIGATION_CONFIRMATION
        assert "Main Gate" in response.spoken_text


class TestClarification:
    def test_navigation_without_destination_asks_for_clarification(self, service):
        response = service.handle(ConversationInput(text="Can you guide me?"))
        assert response.response_type is ConversationResponseType.CLARIFICATION
        assert response.requires_clarification is True
        assert response.context.pending_clarification == "destination"

    def test_information_without_topic_asks_for_clarification(self, service):
        response = service.handle(ConversationInput(text="Tell me about"))
        assert response.response_type is ConversationResponseType.CLARIFICATION
        assert response.context.pending_clarification == "topic"

    def test_answering_a_pending_destination_clarification(self, service):
        first = service.handle(ConversationInput(text="Can you guide me?"))
        assert first.context.pending_clarification == "destination"

        second = service.handle(ConversationInput(text="the library", context=first.context))
        assert second.response_type is ConversationResponseType.NAVIGATION_CONFIRMATION
        assert second.context.pending_clarification is None
        assert second.context.current_destination == "the library"


class TestUnknownRequest:
    def test_gibberish_input_falls_back_gracefully(self, service):
        response = service.handle(ConversationInput(text="asdkjhaskjdh 12345 !!!"))
        assert response.response_type is ConversationResponseType.FALLBACK_UNKNOWN
        assert response.spoken_text

    def test_unknown_request_does_not_raise(self, service):
        # Should never raise, regardless of how strange the input is.
        service.handle(ConversationInput(text="???"))


class TestContextFollowUp:
    def test_where_then_guide_me_there(self, service):
        first = service.handle(ConversationInput(text="Where is the AI Lab?"))
        assert first.context.current_topic == "AI Lab"

        second = service.handle(ConversationInput(
            text="Can you guide me there?", context=first.context,
        ))
        assert second.response_type is ConversationResponseType.NAVIGATION_CONFIRMATION
        assert "AI Lab" in second.spoken_text
        assert second.context.current_destination == "AI Lab"

    def test_turn_count_increments_across_turns(self, service):
        first = service.handle(ConversationInput(text="Hello"))
        second = service.handle(ConversationInput(text="Where is the library?", context=first.context))
        assert first.context.turn_count == 1
        assert second.context.turn_count == 2


class TestArabicReadyBehavior:
    def test_arabic_text_switches_language(self, service):
        response = service.handle(ConversationInput(text="أين المختبر"))
        assert response.language is Language.ARABIC

    def test_arabic_language_persists_across_turns(self, service):
        first = service.handle(ConversationInput(text="مرحبا"))
        assert first.language is Language.ARABIC

        second = service.handle(ConversationInput(text="hello", context=first.context))
        # English-default text should not override an established
        # Arabic conversation language.
        assert second.language is Language.ARABIC

    def test_explicit_language_override(self, service):
        response = service.handle(ConversationInput(text="Hello", language=Language.ARABIC))
        assert response.language is Language.ARABIC


class TestEnglishBehavior:
    def test_default_language_is_english(self, service):
        response = service.handle(ConversationInput(text="Hello"))
        assert response.language is Language.ENGLISH


class TestContextReset:
    def test_reset_intent_clears_topic_and_destination(self, service):
        first = service.handle(ConversationInput(text="Where is the AI Lab?"))
        assert first.context.current_topic == "AI Lab"

        second = service.handle(ConversationInput(text="start over", context=first.context))
        assert second.response_type is ConversationResponseType.CONTEXT_RESET
        assert second.context.current_topic is None
        assert second.context.current_destination is None
        assert second.context.pending_clarification is None

    def test_reset_preserves_language(self, service):
        first = service.handle(ConversationInput(text="مرحبا"))
        second = service.handle(ConversationInput(text="reset", context=first.context))
        assert second.context.language is Language.ARABIC

    def test_service_reset_helper(self, service):
        context = ConversationContext(current_topic="AI Lab", turn_count=5)
        fresh = service.reset(context)
        assert fresh.current_topic is None
        assert fresh.turn_count == 0


class TestMalformedInput:
    def test_none_text_does_not_raise(self, service):
        response = service.handle(ConversationInput(text=None))
        assert response.response_type is ConversationResponseType.MALFORMED_INPUT
        assert response.requires_clarification is True

    def test_empty_string_does_not_raise(self, service):
        response = service.handle(ConversationInput(text=""))
        assert response.response_type is ConversationResponseType.MALFORMED_INPUT

    def test_whitespace_only_does_not_raise(self, service):
        response = service.handle(ConversationInput(text="   \n\t  "))
        assert response.response_type is ConversationResponseType.MALFORMED_INPUT

    def test_non_string_text_does_not_raise(self, service):
        response = service.handle(ConversationInput(text=12345))  # type: ignore[arg-type]
        assert response.response_type is ConversationResponseType.MALFORMED_INPUT


class TestCallerProvidedIntent:
    def test_ml_intent_result_is_honored_over_local_heuristic(self, service):
        # A caller that already ran app.ml.service.MLIntentService can
        # hand its IntentType straight in.
        response = service.handle(ConversationInput(
            text="asdkjh this text has no obvious keywords",
            intent=IntentType.HELP,
        ))
        assert response.response_type is ConversationResponseType.HELP

    def test_unknown_ml_intent_maps_to_fallback(self, service):
        response = service.handle(ConversationInput(
            text="Where is the AI Lab?", intent=IntentType.UNKNOWN,
        ))
        assert response.response_type is ConversationResponseType.FALLBACK_UNKNOWN


class TestConfirmation:
    def test_yes_after_context_acknowledged(self, service):
        response = service.handle(ConversationInput(text="yes"))
        assert response.response_type is ConversationResponseType.CONFIRMATION_ACK

    def test_no_after_context_acknowledged(self, service):
        response = service.handle(ConversationInput(text="no"))
        assert response.response_type is ConversationResponseType.CONFIRMATION_ACK


class TestResponseIsDataclassContract:
    def test_response_is_conversation_response_instance(self, service):
        response = service.handle(ConversationInput(text="Hello"))
        assert isinstance(response, ConversationResponse)
        assert isinstance(response.context, ConversationContext)
