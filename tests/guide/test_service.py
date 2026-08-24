"""
Supplementary behavior tests for app.guide.guide_service.

Complements tests/test_guide.py (which already covers per-topic
retrieval and unknown-topic handling for the current GuideTopic set)
with determinism, cross-topic data-integrity, and public-API-surface
checks called for by P1-GUIDE's own test checklist.
"""

from __future__ import annotations

from app.decision.event_manager import GuideTopic
from app.guide import GuideResponse, GuideService
from app.guide.content import TOPIC_CONTENT


class TestDeterministicOutput:
    def test_repeated_calls_return_equal_content(self):
        service = GuideService()
        first = service.get_topic_content(GuideTopic.AI_PROJECTS)
        second = service.get_topic_content(GuideTopic.AI_PROJECTS)
        assert first.title == second.title
        assert first.summary == second.summary
        assert first.sections == second.sections
        assert first.spoken_text == second.spoken_text

    def test_new_service_instance_gives_same_content(self):
        a = GuideService().get_topic_content(GuideTopic.ROBOTICS)
        b = GuideService().get_topic_content(GuideTopic.ROBOTICS)
        assert a.title == b.title
        assert a.spoken_text == b.spoken_text


class TestDataIntegrity:
    def test_every_guide_topic_has_content(self):
        for topic in GuideTopic:
            assert topic in TOPIC_CONTENT

    def test_no_two_topics_share_identical_spoken_text(self):
        spoken_texts = [content.spoken_text for content in TOPIC_CONTENT.values()]
        assert len(spoken_texts) == len(set(spoken_texts))

    def test_no_two_topics_share_identical_title(self):
        titles = [content.title for content in TOPIC_CONTENT.values()]
        assert len(titles) == len(set(titles))

    def test_all_content_fields_are_non_empty(self):
        for topic, content in TOPIC_CONTENT.items():
            assert content.title.strip(), f"{topic}: empty title"
            assert content.summary.strip(), f"{topic}: empty summary"
            assert content.spoken_text.strip(), f"{topic}: empty spoken_text"
            assert len(content.sections) > 0, f"{topic}: no sections"
            assert all(s.strip() for s in content.sections), f"{topic}: blank section"

    def test_spoken_text_is_reasonably_concise(self):
        # Guide content is meant for robot speech -- not a long essay.
        for topic, content in TOPIC_CONTENT.items():
            word_count = len(content.spoken_text.split())
            assert word_count <= 60, f"{topic}: spoken_text is {word_count} words"


class TestPublicServiceAPI:
    def test_get_topic_content_is_the_only_public_entry_point(self):
        public_methods = [
            name
            for name in dir(GuideService)
            if not name.startswith("_") and callable(getattr(GuideService, name))
        ]
        assert public_methods == ["get_topic_content"]

    def test_response_type_is_guide_response(self):
        service = GuideService()
        response = service.get_topic_content(GuideTopic.LAB_INFORMATION)
        assert isinstance(response, GuideResponse)

    def test_service_is_reusable_across_many_topics(self):
        service = GuideService()
        for topic in GuideTopic:
            response = service.get_topic_content(topic)
            assert response.topic is topic


class TestHardwareIndependence:
    def test_guide_service_requires_no_external_resources(self):
        # Construction and use should succeed with no camera, robot,
        # network, or database -- GuideService takes no such
        # dependencies in its constructor.
        service = GuideService()
        response = service.get_topic_content(GuideTopic.AI_PROJECTS)
        assert response is not None
