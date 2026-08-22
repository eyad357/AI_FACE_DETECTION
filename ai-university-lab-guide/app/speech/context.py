"""
Conversation context — lightweight, local, deterministic per-session
state for the Speech & Conversation layer.

Responsibility: remember just enough about the ongoing conversation to
support short contextual follow-up (e.g. "Can you guide me there?"
after "Where is the AI Lab?"), clarification, and confirmation — and
nothing more.

Explicitly NOT in scope (see phase instructions, "CONTEXT" section):
    - persistent databases
    - complicated memory systems
    - external LLM dependencies
    - network services

ConversationContext is an immutable (frozen) dataclass. A turn never
mutates an existing context in place; app.speech.conversation always
builds a new context via dataclasses.replace(...) and returns it as
part of ConversationResponse. This keeps conversation state fully
deterministic and easy to test (same input context + same
ConversationInput always yields the same output context).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from app.speech.language import Language


@dataclass(frozen=True)
class ConversationContext:
    """
    Lightweight conversation state carried across turns.

    Attributes:
        language: The language this conversation is currently using.
        current_topic: The most recent information topic discussed
            (e.g. "AI Lab"), used for short contextual follow-up such
            as "Can you guide me there?".
        current_destination: The most recent destination the system
            confirmed it would guide the student to.
        last_intent: A short string label for the most recently
            handled intent (e.g. "NAVIGATION", "INFORMATION"). Kept as
            a plain string (not app.speech.intent.IntentType) so this
            context can also represent intents produced by this
            module's own local, non-ML heuristic, which are not
            necessarily IntentType members.
        last_user_text: The raw text of the most recent student
            utterance, kept for traceability/debugging only (not
            re-parsed by consumers).
        pending_clarification: What the system is currently waiting to
            have clarified, if anything (e.g. "destination", "topic").
            None means there is no open clarification.
        turn_count: Number of turns processed so far in this
            conversation (starts at 0 for a fresh context).
    """

    language: Language = Language.ENGLISH
    current_topic: Optional[str] = None
    current_destination: Optional[str] = None
    last_intent: Optional[str] = None
    last_user_text: Optional[str] = None
    pending_clarification: Optional[str] = None
    turn_count: int = 0

    @staticmethod
    def initial(language: Optional[Language] = None) -> "ConversationContext":
        """Build a fresh context for a brand-new conversation."""
        return ConversationContext(language=language or Language.default())

    def reset(self, keep_language: bool = True) -> "ConversationContext":
        """
        Return a brand-new context, optionally preserving the current
        language (the common case — resetting a conversation shouldn't
        force the student to re-establish which language they speak).
        """
        return ConversationContext.initial(
            language=self.language if keep_language else Language.default()
        )

    def with_updates(self, **changes: object) -> "ConversationContext":
        """
        Return a new ConversationContext with the given fields
        replaced. Thin wrapper around dataclasses.replace so callers
        in app.speech.conversation don't need to import `replace`
        themselves.
        """
        return replace(self, **changes)
