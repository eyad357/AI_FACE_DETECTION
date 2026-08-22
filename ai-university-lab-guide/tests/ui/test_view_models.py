"""
Tests for app.ui.view_models (SystemStatus, RouteStep, RouteView,
PlaceInfoView, GuideContentView, NavigationView).

No hardware, network, or camera dependency.
"""

import unittest

from app.ui.view_models import (
    GuideContentView,
    NavigationView,
    PlaceInfoView,
    RouteStep,
    RouteView,
    SystemStatus,
)


class TestSystemStatus(unittest.TestCase):
    def test_all_required_statuses_exist(self):
        expected = {
            "WAITING",
            "LISTENING",
            "PROCESSING",
            "NAVIGATING",
            "ARRIVED",
            "ERROR",
        }
        actual = {member.value for member in SystemStatus}
        self.assertEqual(expected, actual)


class TestRouteStep(unittest.TestCase):
    def test_valid_step(self):
        step = RouteStep(index=1, instruction="Go straight", distance_meters=5.0)
        self.assertEqual(step.index, 1)
        self.assertEqual(step.instruction, "Go straight")

    def test_step_without_distance_or_duration(self):
        step = RouteStep(index=1, instruction="Turn left")
        self.assertIsNone(step.distance_meters)
        self.assertIsNone(step.duration_seconds)

    def test_zero_or_negative_index_rejected(self):
        with self.assertRaises(ValueError):
            RouteStep(index=0, instruction="Go straight")

    def test_empty_instruction_rejected(self):
        with self.assertRaises(ValueError):
            RouteStep(index=1, instruction="   ")

    def test_negative_distance_rejected(self):
        with self.assertRaises(ValueError):
            RouteStep(index=1, instruction="Go straight", distance_meters=-1.0)

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            RouteStep(index=1, instruction="Go straight", duration_seconds=-1.0)


class TestPlaceInfoView(unittest.TestCase):
    def test_valid_place_info(self):
        place = PlaceInfoView(name="Robotics Lab", category="Lab")
        self.assertEqual(place.name, "Robotics Lab")

    def test_empty_name_rejected(self):
        with self.assertRaises(ValueError):
            PlaceInfoView(name="")


class TestRouteView(unittest.TestCase):
    def test_multi_step_route(self):
        steps = [
            RouteStep(index=1, instruction="Go straight", distance_meters=5.0),
            RouteStep(index=2, instruction="Turn left", distance_meters=3.0),
        ]
        route = RouteView(destination_name="Lab 3", steps=steps)
        self.assertEqual(len(route.steps), 2)

    def test_empty_route_is_valid(self):
        route = RouteView(destination_name="Lab 3", steps=[])
        self.assertEqual(route.steps, [])

    def test_empty_destination_name_rejected(self):
        with self.assertRaises(ValueError):
            RouteView(destination_name="")

    def test_negative_total_distance_rejected(self):
        with self.assertRaises(ValueError):
            RouteView(destination_name="Lab 3", total_distance_meters=-1.0)

    def test_negative_total_duration_rejected(self):
        with self.assertRaises(ValueError):
            RouteView(destination_name="Lab 3", total_duration_seconds=-1.0)

    def test_current_step_index_out_of_range_rejected(self):
        steps = [RouteStep(index=1, instruction="Go straight")]
        with self.assertRaises(ValueError):
            RouteView(destination_name="Lab 3", steps=steps, current_step_index=2)

    def test_current_step_index_zero_rejected(self):
        with self.assertRaises(ValueError):
            RouteView(destination_name="Lab 3", current_step_index=0)

    def test_current_step_index_valid_with_no_steps_allowed(self):
        # current_step_index is only range-checked against len(steps)
        # when there ARE steps; with an empty route it is accepted
        # as-is (e.g. "about to depart" bookkeeping upstream).
        route = RouteView(destination_name="Lab 3", steps=[], current_step_index=1)
        self.assertEqual(route.current_step_index, 1)


class TestGuideContentView(unittest.TestCase):
    def test_valid_guide_content(self):
        view = GuideContentView(title="AI Projects", summary="Overview")
        self.assertEqual(view.title, "AI Projects")

    def test_empty_title_rejected(self):
        with self.assertRaises(ValueError):
            GuideContentView(title="", summary="Overview")


class TestNavigationView(unittest.TestCase):
    def test_valid_navigation_view(self):
        view = NavigationView(status=SystemStatus.WAITING)
        self.assertEqual(view.status, SystemStatus.WAITING)
        self.assertIsNone(view.route)

    def test_non_system_status_rejected(self):
        with self.assertRaises(ValueError):
            NavigationView(status="NAVIGATING")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
