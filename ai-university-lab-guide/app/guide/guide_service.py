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
from app.guide.locations import LOCATION_CONTENT, LocationId, LocationRecord
from app.utils.logger import get_logger

logger = get_logger(__name__)

_UNAVAILABLE_TITLE = "Topic Unavailable"
_UNAVAILABLE_SUMMARY = "This topic is not currently available."
_LOCATION_UNAVAILABLE_TITLE = "Location Unavailable"
_LOCATION_UNAVAILABLE_SUMMARY = "This location is not currently available."


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
            or None for a location-based response or an
            unavailable/unsupported topic response.
        title: Short display title.
        summary: One-paragraph overview.
        sections: Ordered list of content sections/paragraphs.
        spoken_text: Short text suitable for robot speech. Guide does
            not perform speech synthesis itself — this is plain text
            for a future orchestration layer to hand to Robot/UI.
        timestamp: When this response was produced.
        location_id: The requested location identifier
            (app.guide.locations.LocationId), if this response came
            from get_location_info() rather than get_topic_content().
            None for topic-based responses. Added additively in the
            Guide-only "G1" phase; existing topic-based callers are
            unaffected since this field defaults to None.
    """

    topic: Optional[GuideTopic]
    title: str
    summary: str
    sections: List[str] = field(default_factory=list)
    spoken_text: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    location_id: Optional[str] = None


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

    def get_location_info(self, location_id: LocationId) -> GuideResponse:
        """
        Retrieve structured information about a university location.

        This is Guide's location-information API — additive alongside
        the existing get_topic_content(), and entirely independent from
        GuideTopic. Guide describes a place here; it never calculates
        how to reach it (that is Navigation's future responsibility,
        not implemented in this phase).

        Args:
            location_id: The requested location identifier. See
                app.guide.locations.LOCATION_CONTENT for valid values.

        Returns:
            A GuideResponse with the location's information
            (topic=None, location_id set to the requested id), or a
            safe "Location Unavailable" response if `location_id` is
            not a non-empty string or has no registered record. Never
            raises for normal invalid input, mirroring
            get_topic_content()'s existing safety behavior.
        """
        logger.info("Guide location requested: %s", location_id)

        if not isinstance(location_id, str) or not location_id.strip():
            logger.warning("Unknown guide location requested: %r", location_id)
            return self._unavailable_location_response(location_id=None)

        record = LOCATION_CONTENT.get(location_id)
        if record is None:
            logger.warning("Unknown guide location requested: %r", location_id)
            return self._unavailable_location_response(location_id=location_id)

        logger.info("Guide location content retrieved for location_id=%s", location_id)
        return GuideResponse(
            topic=None,
            title=record.name,
            summary=record.description,
            sections=self._location_sections(record),
            spoken_text=record.spoken_text,
            location_id=record.location_id,
        )

    @staticmethod
    def _location_sections(record: LocationRecord) -> List[str]:
        """Format a LocationRecord's services/facilities/opening_info into display sections."""
        sections: List[str] = []
        if record.services:
            sections.append("Services: " + ", ".join(record.services))
        if record.facilities:
            sections.append("Facilities: " + ", ".join(record.facilities))
        if record.opening_info:
            sections.append(record.opening_info)
        return sections

    @staticmethod
    def _unavailable_location_response(location_id: Optional[str]) -> GuideResponse:
        return GuideResponse(
            topic=None,
            title=_LOCATION_UNAVAILABLE_TITLE,
            summary=_LOCATION_UNAVAILABLE_SUMMARY,
            sections=[],
            spoken_text=_LOCATION_UNAVAILABLE_SUMMARY,
            location_id=location_id,
        )
