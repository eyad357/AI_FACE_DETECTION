"""
PLACEHOLDER local knowledge — used ONLY as a fallback.

Integration gap (documented in PHASE_REPORT.md): this phase does NOT
own factual location/topic content. That is Guide's job
(app.guide.guide_service.GuideService, spoken_text) for topic
information, and would be Navigation's job
(app.navigation, not yet implemented) for real destinations/routes.

The phase objective's worked example ("Where is the AI Lab?" -> "The
AI Lab is on the second floor of the Engineering Building.") requires
SOME information text to exist even when this module is exercised on
its own, with no caller wired up yet (Guide/Navigation integration is
explicitly out of scope for this phase). Rather than importing
app.guide (which this phase does not own and was told to prefer a
"Speech-owned local adapter" over reaching into another module's data
when no compatible shared contract exists), this file holds a small,
clearly-labeled, static placeholder lookup.

Callers that HAVE real content (e.g. a future app.main orchestrator
that already called GuideService.get_topic_content()) should pass it
in via `ConversationInput.information_text` /
`ConversationInput.destination` — those always take precedence over
this placeholder lookup. See app/speech/conversation.py.

This is intentionally tiny, static, offline, and deterministic — not a
knowledge base, not a database, not a substitute for Guide/Navigation.
"""

from __future__ import annotations

from typing import Dict, Optional

# Keys are lowercased, whitespace-normalized topic/location names.
_PLACEHOLDER_LOCATIONS: Dict[str, str] = {
    "ai lab": "The AI Lab is on the second floor of the Engineering Building.",
    "robotics lab": "The Robotics Lab is on the second floor of the Engineering Building, next to the AI Lab.",
    "library": "The Library is on the ground floor of the Main Building.",
    "admissions office": "The Admissions Office is on the ground floor of the Main Building, near the entrance.",
}


def normalize_topic(text: str) -> str:
    """Lowercase + collapse whitespace, for stable dict lookups."""
    return " ".join(text.strip().lower().split())


def lookup_placeholder_information(topic: str) -> Optional[str]:
    """
    Return placeholder information text for a known placeholder
    topic/location name, or None if `topic` isn't in the placeholder
    set. Never raises for unexpected input.
    """
    if not isinstance(topic, str) or not topic.strip():
        return None
    return _PLACEHOLDER_LOCATIONS.get(normalize_topic(topic))


def known_placeholder_topics() -> Dict[str, str]:
    """Read-only view of the placeholder table (used by tests/docs)."""
    return dict(_PLACEHOLDER_LOCATIONS)
