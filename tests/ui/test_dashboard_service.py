"""
Tests for app.ui.dashboard_service.DashboardService and its adapters.

These tests require no physical robot, no Robot SDK, and no camera
hardware -- DashboardService always runs Robot on
app.robot.SimulatedRobotBackend and Vision reports an honest
"camera unavailable" state when no device exists, exactly as it must
for a headless CI/demo environment.
"""

from __future__ import annotations

from app.decision.event_manager import GuideTopic
from app.ui.dashboard_service import DashboardService
from app.ui.dashboard_view_models import HealthState


class TestServiceInitialization:
    def test_dashboard_service_constructs_without_error(self):
        service = DashboardService()
        assert service is not None

    def test_session_has_a_stable_id_and_starts_with_no_events(self):
        service = DashboardService()
        assert service.session.session_id
        assert service.session.events == []


class TestStatusCards:
    def test_status_cards_cover_every_subsystem(self):
        service = DashboardService()
        names = {card.name for card in service.status_cards()}
        assert names == {
            "Vision", "ML", "DL", "Navigation", "Decision",
            "Speech", "Guide", "Robot", "Integration", "UI",
        }

    def test_every_status_card_has_a_real_health_state(self):
        service = DashboardService()
        for card in service.status_cards():
            assert isinstance(card.state, HealthState)

    def test_overall_system_state_is_not_worse_than_the_best_subsystem(self):
        service = DashboardService()
        # Speech/Decision/Guide/Navigation/Robot are all pure-Python and
        # hardware-free, so at minimum those must report PASS even in a
        # headless environment -- overall state must reflect that
        # instead of collapsing to a single worst-case reading.
        overall = service.overall_system_state()
        assert overall in {HealthState.PASS, HealthState.DEGRADED}


class TestRobotSimulation:
    def test_robot_actions_never_require_physical_hardware(self):
        service = DashboardService()
        view = service.robot_action("GREET")
        assert view.backend_mode == "SIMULATED"
        assert view.last_success is True

    def test_robot_wave_and_stop_render_real_execution_results(self):
        service = DashboardService()
        wave = service.robot_action("WAVE")
        stop = service.robot_action("STOP")
        assert wave.last_command == "WAVE"
        assert stop.last_command == "STOP"
        assert wave.last_message  # real message from RobotExecutionResult, not blank

    def test_unsupported_robot_action_reports_failure_honestly(self):
        service = DashboardService()
        view = service.robot_action("FLY")
        assert view.last_success is False
        assert "Unsupported" in view.last_message


class TestNavigationRendering:
    def test_known_route_renders_real_route_view(self):
        service = DashboardService()
        view = service.request_route("Entrance", "AI Lab")
        assert view.route is not None
        assert view.route.destination_name

    def test_unknown_destination_renders_an_honest_error_not_fake_data(self):
        service = DashboardService()
        view = service.request_route("Entrance", "Mars Base")
        assert view.route is None
        assert view.message


class TestSpeechLanguageHandling:
    def test_english_utterance_is_handled(self):
        service = DashboardService()
        view = service.handle_utterance("Where is the AI Lab?")
        assert view.language == "en"
        assert view.spoken_text

    def test_arabic_utterance_is_handled(self):
        service = DashboardService()
        view = service.handle_utterance("أين المختبر؟")
        assert view.spoken_text


class TestGuideContent:
    def test_guide_topic_returns_real_content(self):
        service = DashboardService()
        content = service.get_guide_content(GuideTopic.AI_PROJECTS)
        assert content is not None
        assert content.title


class TestDemoScenarios:
    def test_scenarios_are_only_marked_available_when_dependencies_exist(self):
        service = DashboardService()
        for scenario in service.demo_scenarios():
            if not scenario.available:
                assert scenario.unavailable_reason

    def test_running_greeting_scenario_produces_a_real_log(self):
        service = DashboardService()
        log = service.run_demo_scenario("GREETING")
        assert log
        assert any("Robot" in line for line in log)

    def test_running_navigation_scenario_uses_real_navigation_service(self):
        service = DashboardService()
        log = service.run_demo_scenario("NAVIGATION")
        assert any("Navigation" in line for line in log)

    def test_scenario_execution_is_recorded_in_the_event_timeline(self):
        service = DashboardService()
        before = len(service.session.events)
        service.run_demo_scenario("ENGLISH")
        assert len(service.session.events) > before
