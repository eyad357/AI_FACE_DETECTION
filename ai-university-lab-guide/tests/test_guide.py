"""
Tests for app.guide (GuideService / GuideResponse / content).

These tests require no Robot, Robot SDK, camera, Vision, UI, database,
or network access. They only use the existing GuideTopic enum
(app.decision.event_manager.GuideTopic), imported as a plain data
contract — Guide's own tests never touch Decision's state machine.
"""

import pytest

from app.decision.event_manager import GuideTopic
from app.guide import GuideResponse, GuideService
from app.guide.content import TOPIC_CONTENT


@pytest.fixture()
def service() -> GuideService:
    return GuideService()


class TestGuideServiceInitialization:
    def test_initializes_without_error(self):
        GuideService()  # should not raise


class TestTopicContent:
    def test_ai_projects_content_is_returned(self, service):
        response = service.get_topic_content(GuideTopic.AI_PROJECTS)
        assert response.topic is GuideTopic.AI_PROJECTS
        assert response.title
        assert response.summary

    def test_robotics_content_is_returned(self, service):
        response = service.get_topic_content(GuideTopic.ROBOTICS)
        assert response.topic is GuideTopic.ROBOTICS
        assert response.title
        assert response.summary

    def test_training_content_is_returned(self, service):
        response = service.get_topic_content(GuideTopic.TRAINING)
        assert response.topic is GuideTopic.TRAINING
        assert response.title
        assert response.summary

    def test_lab_information_content_is_returned(self, service):
        response = service.get_topic_content(GuideTopic.LAB_INFORMATION)
        assert response.topic is GuideTopic.LAB_INFORMATION
        assert response.title
        assert response.summary

    def test_all_guide_topics_have_registered_content(self):
        for topic in GuideTopic:
            assert topic in TOPIC_CONTENT


class TestUnknownTopicHandling:
    def test_unknown_topic_returns_controlled_response(self, service):
        response = service.get_topic_content("NOT_A_REAL_TOPIC")  # type: ignore[arg-type]
        assert response.topic is None
        assert response.title == "Topic Unavailable"
        assert response.summary

    def test_none_topic_returns_controlled_response(self, service):
        response = service.get_topic_content(None)  # type: ignore[arg-type]
        assert response.topic is None
        assert response.title == "Topic Unavailable"

    def test_unknown_topic_does_not_raise(self, service):
        # Should not raise for any normal invalid input.
        service.get_topic_content(12345)  # type: ignore[arg-type]
        service.get_topic_content([])  # type: ignore[arg-type]
        service.get_topic_content("")  # type: ignore[arg-type]


class TestGuideResponseStructure:
    def test_response_is_guide_response_instance(self, service):
        response = service.get_topic_content(GuideTopic.AI_PROJECTS)
        assert isinstance(response, GuideResponse)

    def test_response_has_required_fields(self, service):
        response = service.get_topic_content(GuideTopic.ROBOTICS)
        assert isinstance(response.title, str) and response.title
        assert isinstance(response.summary, str) and response.summary
        assert isinstance(response.sections, list)
        assert isinstance(response.spoken_text, str)
        assert response.timestamp is not None

    def test_response_sections_are_non_empty_for_known_topics(self, service):
        for topic in GuideTopic:
            response = service.get_topic_content(topic)
            assert len(response.sections) > 0

    def test_spoken_text_available_for_known_topics(self, service):
        for topic in GuideTopic:
            response = service.get_topic_content(topic)
            assert response.spoken_text.strip() != ""

    def test_unavailable_response_has_empty_sections(self, service):
        response = service.get_topic_content("BOGUS")  # type: ignore[arg-type]
        assert response.sections == []


class TestGuideIndependence:
    def test_guide_service_module_has_no_robot_import(self):
        import app.guide.guide_service as mod

        source = open(mod.__file__).read()
        assert "app.robot" not in source
        assert "robot_controller" not in source
        assert "robot_commands" not in source

    def test_guide_service_module_has_no_vision_import(self):
        import app.guide.guide_service as mod

        source = open(mod.__file__).read()
        assert "app.vision" not in source
        assert "import cv2" not in source

    def test_guide_content_module_has_no_robot_or_vision_import(self):
        import app.guide.content as mod

        source = open(mod.__file__).read()
        assert "app.robot" not in source
        assert "app.vision" not in source

    def test_guide_does_not_import_decision_state_manager(self):
        import ast

        import app.guide.guide_service as service_mod
        import app.guide.content as content_mod

        for mod in (service_mod, content_mod):
            tree = ast.parse(open(mod.__file__).read())
            imported_modules = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    imported_modules.append(node.module)
                elif isinstance(node, ast.Import):
                    imported_modules.extend(alias.name for alias in node.names)
            assert "app.decision.state_manager" not in imported_modules
            assert "app.robot" not in imported_modules
            assert "app.vision" not in imported_modules

    def test_guide_runs_independently(self):
        # No camera, no Robot, no Decision state machine involved at all
        # -- only the plain GuideTopic enum value.
        service = GuideService()
        response = service.get_topic_content(GuideTopic.TRAINING)
        assert response.topic is GuideTopic.TRAINING
