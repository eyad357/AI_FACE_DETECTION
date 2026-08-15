"""
Guide service.

Responsibility: answer "what information should be provided?" Given a
topic, return a structured GuideResponse built from static content in
app.guide.content.

Guide does NOT:
    - decide whether a visitor exists (Decision's job)
    - manage application state or transitions (Decision's job)
    - control the Robot or perform speech synthesis (Robot's job)
    - render UI (UI's job)
    - orchestrate the application (main.py's job)

Guide reuses the single existing GuideTopic contract
(app.decision.event_manager.GuideTopic) rather than duplicating it.
This is the ONLY symbol Guide imports from app.decision — it does NOT
import app.decision.state_manager and knows nothing about Decision
states, transitions, or DecisionEvent handling. See
docs/integration_contract.md for the full boundary rationale.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from app.decision.event_manager import GuideTopic
from app.guide.content import TOPIC_CONTENT
from app.utils.logger import get_logger

logger = get_logger(__name__)

_UNAVAILABLE_TITLE = "Topic Unavailable"
_UNAVAILABLE_SUMMARY = "This topic is not currently available."


@dataclass(frozen=True)
class GuideResponse:
    """
    Structured content response produced by GuideService.

    This is Guide's own output contract. No equivalent model existed in
    app.models.schemas at the time this was added, so it was kept here
    in app.guide rather than in app/models/schemas.py — the same
    pattern already used by DecisionEvent, which lives in
    app.decision.event_manager rather than app.models. Keeping it here
    also avoids introducing an app.models -> app.decision dependency
    (GuideResponse.topic reuses the existing GuideTopic enum), which
    would violate app/models/schemas.py's explicit "no app-internal
    imports" contract.

    Attributes:
        topic: The requested topic (app.decision.event_manager.GuideTopic),
            or None for an unavailable/unsupported topic response.
        title: Short display title.
        summary: One-paragraph overview.
        sections: Ordered list of content sections/paragraphs.
        spoken_text: Short text suitable for robot speech. Guide does
            not perform speech synthesis itself — this is plain text
            for a future orchestration layer to hand to Robot/UI.
        timestamp: When this response was produced.
    """

    topic: Optional[GuideTopic]
    title: str
    summary: str
    sections: List[str] = field(default_factory=list)
    spoken_text: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class GuideService:
    """
    Retrieves and formats guide content for a requested topic.

    Usage:
        service = GuideService()
        response = service.get_topic_content(GuideTopic.AI_PROJECTS)
    """

    def __init__(self) -> None:
        logger.info("Guide service initialized")

    def get_topic_content(self, topic: GuideTopic) -> GuideResponse:
        """
        Retrieve structured content for a topic.

        Args:
            topic: The requested GuideTopic.

        Returns:
            A GuideResponse with the topic's content, or a safe
            "Topic Unavailable" response if `topic` is not a valid
            GuideTopic member or has no registered content. Never
            raises for normal invalid input (Rule: no uncontrolled
            exceptions for normal invalid user input).
        """
        logger.info("Guide topic requested: %s", getattr(topic, "value", topic))

        if not isinstance(topic, GuideTopic):
            logger.warning("Unknown guide topic requested: %r", topic)
            return self._unavailable_response(topic=None)

        content = TOPIC_CONTENT.get(topic)
        if content is None:
            # Should not happen given TOPIC_CONTENT covers every
            # GuideTopic member, but handled explicitly rather than
            # relying on that invariant silently.
            logger.error("No content registered for topic=%s", topic.value)
            return self._unavailable_response(topic=topic)

        logger.info("Guide content retrieved for topic=%s", topic.value)
        return GuideResponse(
            topic=topic,
            title=content.title,
            summary=content.summary,
            sections=list(content.sections),
            spoken_text=content.spoken_text,
        )

    @staticmethod
    def _unavailable_response(topic: Optional[GuideTopic]) -> GuideResponse:
        return GuideResponse(
            topic=topic,
            title=_UNAVAILABLE_TITLE,
            summary=_UNAVAILABLE_SUMMARY,
            sections=[],
            spoken_text=_UNAVAILABLE_SUMMARY,
        )
