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

    def test_guide_service_module_has_no_ml_dl_navigation_import(self):
        # app.ml / app.dl / app.navigation did not exist when this test
        # file was first written (Phase 3); added here (Phase G1) now
        # that they do, to explicitly pin the same independence
        # guarantee for Person 1's parallel modules.
        import ast

        import app.guide.content as content_mod
        import app.guide.guide_service as service_mod
        import app.guide.locations as locations_mod

        for mod in (service_mod, content_mod, locations_mod):
            tree = ast.parse(open(mod.__file__).read())
            imported_modules = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    imported_modules.append(node.module)
                elif isinstance(node, ast.Import):
                    imported_modules.extend(alias.name for alias in node.names)
            forbidden = {"app.ml", "app.dl", "app.navigation", "app.main"}
            assert not (forbidden & set(imported_modules))


class TestLocationContent:
    """
    Phase G1: tests for GuideService.get_location_info(), additive
    alongside the existing get_topic_content() tests above. Uses only
    the new, independent app.guide.locations surface.
    """

    def test_ai_lab_location_is_returned(self, service):
        response = service.get_location_info("ai_lab")
        assert response.location_id == "ai_lab"
        assert response.title == "AI Lab"
        assert response.summary
        assert response.topic is None  # location responses never set topic

    def test_all_prototype_locations_return_valid_content(self, service):
        from app.guide.locations import LOCATION_CONTENT

        for location_id in LOCATION_CONTENT:
            response = service.get_location_info(location_id)
            assert response.location_id == location_id
            assert response.title
            assert response.summary
            assert response.spoken_text.strip() != ""

    def test_all_ten_suggested_prototype_locations_exist(self):
        from app.guide.locations import LOCATION_CONTENT

        expected_ids = {
            "ai_lab", "robotics_lab", "computer_lab", "library",
            "engineering_building", "student_affairs", "main_auditorium",
            "innovation_lab", "lecture_rooms", "cafeteria",
        }
        assert expected_ids <= set(LOCATION_CONTENT.keys())


class TestUnknownLocationHandling:
    def test_unknown_location_returns_controlled_response(self, service):
        response = service.get_location_info("not_a_real_place")
        assert response.title == "Location Unavailable"
        assert response.summary
        assert response.location_id == "not_a_real_place"

    def test_empty_string_location_handled_safely(self, service):
        response = service.get_location_info("")
        assert response.title == "Location Unavailable"
        assert response.location_id is None

    def test_whitespace_only_location_handled_safely(self, service):
        response = service.get_location_info("   ")
        assert response.title == "Location Unavailable"

    def test_none_location_handled_safely(self, service):
        response = service.get_location_info(None)  # type: ignore[arg-type]
        assert response.title == "Location Unavailable"
        assert response.location_id is None

    def test_non_string_location_does_not_raise(self, service):
        service.get_location_info(12345)  # type: ignore[arg-type]
        service.get_location_info([])  # type: ignore[arg-type]
        service.get_location_info({"id": "ai_lab"})  # type: ignore[arg-type]


class TestGuideResponseLocationField:
    def test_location_id_field_defaults_to_none_for_topic_responses(self, service):
        response = service.get_topic_content(GuideTopic.ROBOTICS)
        assert response.location_id is None

    def test_location_response_has_none_topic(self, service):
        response = service.get_location_info("library")
        assert response.topic is None

    def test_existing_guide_response_construction_still_works_without_location_id(self):
        # Backward-compatibility check: constructing a GuideResponse the
        # old way (no location_id argument) must still work, since the
        # new field has a default.
        response = GuideResponse(
            topic=GuideTopic.TRAINING,
            title="Training & Learning Opportunities",
            summary="...",
        )
        assert response.location_id is None


class TestLocationDataConsistency:
    """
    Data-consistency checks for LOCATION_CONTENT, mirroring the kind of
    guarantee test_all_guide_topics_have_registered_content already
    provides for TOPIC_CONTENT.
    """

    def test_location_content_keys_match_record_location_id(self):
        from app.guide.locations import LOCATION_CONTENT

        for key, record in LOCATION_CONTENT.items():
            assert key == record.location_id

    def test_no_duplicate_location_names(self):
        from app.guide.locations import LOCATION_CONTENT

        names = [record.name for record in LOCATION_CONTENT.values()]
        assert len(names) == len(set(names))

    def test_every_location_has_non_empty_required_fields(self):
        from app.guide.locations import LOCATION_CONTENT

        for record in LOCATION_CONTENT.values():
            assert record.location_id.strip() != ""
            assert record.name.strip() != ""
            assert record.building.strip() != ""
            assert record.description.strip() != ""
            assert record.spoken_text.strip() != ""

    def test_location_content_has_no_navigation_fields(self):
        # Enforces the Guide-vs-Navigation field-ownership split: Guide
        # must never store coordinates, waypoints, routes, or distances.
        from app.guide.locations import LocationRecord

        field_names = set(LocationRecord.__dataclass_fields__.keys())
        forbidden = {
            "coordinates", "latitude", "longitude", "waypoints",
            "route", "distance", "directions", "path",
        }
        assert not (forbidden & field_names)

    def test_realistic_content_not_placeholder_text(self):
        from app.guide.locations import LOCATION_CONTENT

        placeholder_markers = ("lorem ipsum", "todo", "placeholder", "xxx", "tbd")
        for record in LOCATION_CONTENT.values():
            text = (record.description + " " + record.spoken_text).lower()
            for marker in placeholder_markers:
                assert marker not in text

    def test_spoken_text_is_reasonably_concise(self):
        # Spoken text should be speakable in one breath -- a loose upper
        # bound catches accidental essay-length content, not a strict
        # style rule.
        from app.guide.locations import LOCATION_CONTENT

        for record in LOCATION_CONTENT.values():
            assert len(record.spoken_text) < 400


class TestExistingTopicContentDataConsistency:
    """
    Same style of data-consistency check applied to the pre-existing
    TOPIC_CONTENT, filling the gap noted in the Phase A audit -- purely
    additive, does not alter TOPIC_CONTENT or any existing behavior.
    """

    def test_no_placeholder_text_in_topic_content(self):
        from app.guide.content import TOPIC_CONTENT

        placeholder_markers = ("lorem ipsum", "todo", "placeholder", "xxx", "tbd")
        for content in TOPIC_CONTENT.values():
            text = (content.summary + " " + content.spoken_text).lower()
            for marker in placeholder_markers:
                assert marker not in text

    def test_topic_content_titles_are_unique(self):
        from app.guide.content import TOPIC_CONTENT

        titles = [content.title for content in TOPIC_CONTENT.values()]
        assert len(titles) == len(set(titles))

