"""
Tests for app.ui.adapters.robot_adapter.DashboardRobotAdapter.

Requires no physical robot -- always runs against
app.robot.SimulatedRobotBackend via the existing, unmodified
RobotIntegrationAdapter.
"""

from __future__ import annotations

from app.ui.adapters.robot_adapter import DashboardRobotAdapter


class TestDashboardRobotAdapter:
    def test_greet_uses_simulated_backend(self):
        adapter = DashboardRobotAdapter()
        view = adapter.greet()
        assert view.backend_mode == "SIMULATED"
        assert view.last_success is True

    def test_explain_topics_delegate_to_existing_adapter_methods(self):
        adapter = DashboardRobotAdapter()
        view = adapter.explain("EXPLAIN_AI", "AI is the study of intelligent agents.")
        assert view.last_command == "EXPLAIN_AI"
        assert view.last_success is True

    def test_unknown_explain_topic_is_rejected_safely(self):
        adapter = DashboardRobotAdapter()
        view = adapter.explain("EXPLAIN_QUANTUM", "text")
        assert view.last_success is False

    def test_integration_status_reports_pass_when_adapter_is_ready(self):
        adapter = DashboardRobotAdapter()
        status = adapter.integration_status()
        assert status.name == "Integration"
