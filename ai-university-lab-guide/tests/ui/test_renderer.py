"""
Tests for app.ui.renderer (TextRenderer).

No camera, Robot, or network dependency. Output is asserted as plain
text content, not exact pixel/console formatting, so these tests stay
stable if cosmetic spacing changes.
"""

import unittest

from app.ui.route_display import (
    arrived_view,
    build_place_info_view,
    build_route_view,
    empty_destination_view,
    error_view,
    navigating_view,
    unknown_destination_view,
)
from app.ui.renderer import TextRenderer
from app.ui.view_models import GuideContentView, SystemStatus


class TestRenderStatus(unittest.TestCase):
    def setUp(self):
        self.renderer = TextRenderer()

    def test_all_statuses_render_without_error(self):
        for status in SystemStatus:
            text = self.renderer.render_status(status)
            self.assertIsInstance(text, str)
            self.assertTrue(text)


class TestRenderNavigation(unittest.TestCase):
    def setUp(self):
        self.renderer = TextRenderer()

    def test_multi_step_route_renders_destination_and_steps(self):
        route = build_route_view(
            "Lab 3",
            steps=[("Go straight", 5.0, 4.0), ("Turn left", 3.0, 2.0)],
            total_distance_meters=8.0,
            total_duration_seconds=6.0,
        )
        view = navigating_view(route)
        text = self.renderer.render_navigation(view)
        self.assertIn("Lab 3", text)
        self.assertIn("Go straight", text)
        self.assertIn("Turn left", text)
        self.assertIn("Navigating", text)

    def test_current_step_is_marked(self):
        route = build_route_view(
            "Lab 3",
            steps=[("Go straight", 5.0, 4.0), ("Turn left", 3.0, 2.0)],
            current_step_index=2,
        )
        view = navigating_view(route)
        text = self.renderer.render_navigation(view)
        lines = text.splitlines()
        marked = [line for line in lines if line.startswith(">")]
        self.assertEqual(len(marked), 1)
        self.assertIn("Turn left", marked[0])

    def test_empty_route_renders_placeholder(self):
        route = build_route_view("Lab 3")
        view = navigating_view(route)
        text = self.renderer.render_navigation(view)
        self.assertIn("no intermediate steps", text)

    def test_arrival_state_renders(self):
        place = build_place_info_view("Lab 3", description="The robotics lab")
        view = arrived_view("Lab 3", place_info=place)
        text = self.renderer.render_navigation(view)
        self.assertIn("Arrived", text)
        self.assertIn("Lab 3", text)
        self.assertIn("robotics lab", text)

    def test_error_state_renders(self):
        view = error_view("Something failed")
        text = self.renderer.render_navigation(view)
        self.assertIn("Error", text)
        self.assertIn("Something failed", text)

    def test_unknown_destination_renders(self):
        view = unknown_destination_view("Atlantis")
        text = self.renderer.render_navigation(view)
        self.assertIn("Error", text)
        self.assertIn("Atlantis", text)

    def test_empty_destination_renders_waiting(self):
        view = empty_destination_view()
        text = self.renderer.render_navigation(view)
        self.assertIn("Waiting", text)

    def test_place_info_without_route_still_renders(self):
        place = build_place_info_view("Lab 3", category="Lab")
        from app.ui.view_models import NavigationView

        view = NavigationView(
            status=SystemStatus.PROCESSING,
            destination_name="Lab 3",
            place_info=place,
        )
        text = self.renderer.render_navigation(view)
        self.assertIn("Processing", text)
        self.assertIn("Lab 3", text)
        self.assertIn("Category: Lab", text)


class TestRenderGuide(unittest.TestCase):
    def setUp(self):
        self.renderer = TextRenderer()

    def test_guide_content_renders_title_and_summary(self):
        view = GuideContentView(
            title="AI Projects",
            summary="Overview of AI work",
            sections=["Section one.", "Section two."],
        )
        text = self.renderer.render_guide(view)
        self.assertIn("AI Projects", text)
        self.assertIn("Overview of AI work", text)
        self.assertIn("Section one.", text)
        self.assertIn("Section two.", text)

    def test_guide_content_without_sections_still_renders(self):
        view = GuideContentView(title="Topic Unavailable", summary="Not available.")
        text = self.renderer.render_guide(view)
        self.assertIn("Topic Unavailable", text)


if __name__ == "__main__":
    unittest.main()
