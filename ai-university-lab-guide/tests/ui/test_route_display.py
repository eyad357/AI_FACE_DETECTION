"""
Tests for app.ui.route_display (builders/adapters).

Uses only synthetic, plain input data plus the existing, stable
app.guide.guide_service.GuideResponse/GuideService contract. No
camera, Robot, network, or app.navigation dependency (app.navigation
is an unimplemented placeholder as of this phase — see
app/navigation/__init__.py and PHASE_REPORT.md).
"""

import unittest

from app.decision.event_manager import GuideTopic
from app.guide.guide_service import GuideService
from app.ui.route_display import (
    arrived_view,
    build_navigation_view_safe,
    build_place_info_view,
    build_route_view,
    empty_destination_view,
    error_view,
    guide_response_to_view,
    navigating_view,
    unknown_destination_view,
)
from app.ui.view_models import SystemStatus


class TestBuildRouteView(unittest.TestCase):
    def test_multi_step_route(self):
        route = build_route_view(
            "Lab 3",
            steps=[("Go straight", 5.0, 4.0), ("Turn left", 3.0, 2.0)],
            total_distance_meters=8.0,
            total_duration_seconds=6.0,
        )
        self.assertEqual(route.destination_name, "Lab 3")
        self.assertEqual(len(route.steps), 2)
        self.assertEqual(route.steps[0].index, 1)
        self.assertEqual(route.steps[1].index, 2)

    def test_empty_route(self):
        route = build_route_view("Lab 3")
        self.assertEqual(route.steps, [])

    def test_steps_without_distance_or_duration(self):
        route = build_route_view("Lab 3", steps=[("Go straight", None, None)])
        self.assertIsNone(route.steps[0].distance_meters)

    def test_malformed_step_raises(self):
        with self.assertRaises(ValueError):
            build_route_view("Lab 3", steps=[("only one field",)])  # type: ignore[list-item]

    def test_invalid_destination_raises(self):
        with self.assertRaises(ValueError):
            build_route_view("")


class TestControlledViews(unittest.TestCase):
    def test_unknown_destination_view(self):
        view = unknown_destination_view("Atlantis")
        self.assertEqual(view.status, SystemStatus.ERROR)
        self.assertEqual(view.destination_name, "Atlantis")
        self.assertTrue(view.message)

    def test_unknown_destination_view_with_no_name(self):
        view = unknown_destination_view(None)
        self.assertEqual(view.status, SystemStatus.ERROR)
        self.assertIsNone(view.destination_name)

    def test_empty_destination_view(self):
        view = empty_destination_view()
        self.assertEqual(view.status, SystemStatus.WAITING)
        self.assertIsNone(view.destination_name)

    def test_navigating_view(self):
        route = build_route_view("Lab 3", steps=[("Go straight", 5.0, 4.0)])
        view = navigating_view(route)
        self.assertEqual(view.status, SystemStatus.NAVIGATING)
        self.assertEqual(view.destination_name, "Lab 3")
        self.assertIs(view.route, route)

    def test_arrived_view(self):
        place = build_place_info_view("Lab 3", description="The robotics lab")
        view = arrived_view("Lab 3", place_info=place)
        self.assertEqual(view.status, SystemStatus.ARRIVED)
        self.assertIn("Lab 3", view.message)
        self.assertIs(view.place_info, place)

    def test_arrived_view_without_place_info(self):
        view = arrived_view("Lab 3")
        self.assertIsNone(view.place_info)

    def test_error_view_default_message(self):
        view = error_view()
        self.assertEqual(view.status, SystemStatus.ERROR)
        self.assertTrue(view.message)

    def test_error_view_custom_message(self):
        view = error_view("Custom failure")
        self.assertEqual(view.message, "Custom failure")


class TestBuildNavigationViewSafe(unittest.TestCase):
    def test_valid_input_produces_navigating_view(self):
        view = build_navigation_view_safe(
            "Lab 3", steps=[("Go straight", 5.0, 4.0)]
        )
        self.assertEqual(view.status, SystemStatus.NAVIGATING)
        self.assertEqual(len(view.route.steps), 1)

    def test_missing_destination_produces_waiting_view(self):
        view = build_navigation_view_safe(None)
        self.assertEqual(view.status, SystemStatus.WAITING)

    def test_blank_destination_produces_waiting_view(self):
        view = build_navigation_view_safe("   ")
        self.assertEqual(view.status, SystemStatus.WAITING)

    def test_malformed_step_produces_error_view_not_exception(self):
        # Regression guard: malformed upstream input must never raise
        # out of this "safe" builder.
        view = build_navigation_view_safe("Lab 3", steps=[("bad",)])  # type: ignore[list-item]
        self.assertEqual(view.status, SystemStatus.ERROR)
        self.assertTrue(view.message)

    def test_negative_distance_produces_error_view(self):
        view = build_navigation_view_safe(
            "Lab 3", total_distance_meters=-5.0
        )
        self.assertEqual(view.status, SystemStatus.ERROR)

    def test_place_info_is_attached_when_provided(self):
        place = build_place_info_view("Lab 3")
        view = build_navigation_view_safe("Lab 3", place_info=place)
        self.assertIs(view.place_info, place)


class TestGuideResponseAdapter(unittest.TestCase):
    def test_adapts_real_guide_response(self):
        response = GuideService().get_topic_content(GuideTopic.AI_PROJECTS)
        view = guide_response_to_view(response)
        self.assertEqual(view.title, response.title)
        self.assertEqual(view.summary, response.summary)
        self.assertEqual(view.sections, list(response.sections))
        self.assertEqual(view.spoken_text, response.spoken_text)

    def test_adapts_unavailable_guide_response(self):
        response = GuideService().get_topic_content("NOT_A_TOPIC")  # type: ignore[arg-type]
        view = guide_response_to_view(response)
        self.assertEqual(view.title, "Topic Unavailable")


if __name__ == "__main__":
    unittest.main()
