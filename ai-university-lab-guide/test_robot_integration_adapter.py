"""
Tests for the Robot Integration Adapter phase
(app.integration.robot_adapter).

These tests require no physical robot, no Robot SDK, no network, no
Vision, no ML, no DL, no Navigation, no Decision, no Guide, and no UI.
`RobotIntegrationAdapter`'s default backend is `RobotController()`,
whose own default backend is `SimulatedRobotBackend` — deterministic
and hardware-free by design, exactly like the existing Robot tests.
"""

import ast

import pytest

from app.integration import AdapterError, RobotIntegrationAdapter
from app.integration.robot_adapter import _EXPLAIN_COMMAND_TYPES
from app.robot import (
    RobotBackend,
    RobotCommandType,
    RobotController,
    RobotExecutionResult,
    SimulatedRobotBackend,
)


class TestModuleImports:
    def test_adapter_module_imports_successfully(self):
        assert RobotIntegrationAdapter is not None
        assert AdapterError is not None


class TestAdapterInitialization:
    def test_initializes_with_default_robot_controller(self):
        adapter = RobotIntegrationAdapter()
        assert isinstance(adapter._robot_controller, RobotController)
        assert isinstance(adapter._robot_controller._backend, SimulatedRobotBackend)

    def test_initializes_with_custom_robot_controller(self):
        robot_controller = RobotController()
        adapter = RobotIntegrationAdapter(robot_controller=robot_controller)
        assert adapter._robot_controller is robot_controller


class TestSupportedActions:
    """
    Every action here corresponds to an existing RobotCommandType --
    the adapter provides one high-level method per existing Robot
    capability, and nothing else.
    """

    @pytest.fixture()
    def adapter(self) -> RobotIntegrationAdapter:
        return RobotIntegrationAdapter()

    def test_execute_greeting(self, adapter):
        result = adapter.execute_greeting()
        assert isinstance(result, RobotExecutionResult)
        assert result.success is True
        assert result.command_type is RobotCommandType.GREET

    def test_wave(self, adapter):
        result = adapter.wave()
        assert result.success is True
        assert result.command_type is RobotCommandType.WAVE

    def test_speak(self, adapter):
        result = adapter.speak("Welcome to the lab.")
        assert result.success is True
        assert result.command_type is RobotCommandType.SPEAK

    def test_idle(self, adapter):
        result = adapter.idle()
        assert result.success is True
        assert result.command_type is RobotCommandType.IDLE

    def test_stop(self, adapter):
        result = adapter.stop()
        assert result.success is True
        assert result.command_type is RobotCommandType.STOP

    def test_explain_ai(self, adapter):
        result = adapter.explain_ai("AI research overview.")
        assert result.success is True
        assert result.command_type is RobotCommandType.EXPLAIN_AI

    def test_explain_robotics(self, adapter):
        result = adapter.explain_robotics("Robotics program overview.")
        assert result.success is True
        assert result.command_type is RobotCommandType.EXPLAIN_ROBOTICS

    def test_explain_training(self, adapter):
        result = adapter.explain_training("Training offered overview.")
        assert result.success is True
        assert result.command_type is RobotCommandType.EXPLAIN_TRAINING

    def test_explain_lab(self, adapter):
        result = adapter.explain_lab("Lab overview.")
        assert result.success is True
        assert result.command_type is RobotCommandType.EXPLAIN_LAB

    def test_every_existing_command_type_has_an_adapter_method(self):
        # There is a named adapter method for every one of the nine
        # existing RobotCommandType members -- no gaps, no extras.
        adapter = RobotIntegrationAdapter()
        method_names = {
            "execute_greeting", "wave", "speak", "idle", "stop",
            "explain_ai", "explain_robotics", "explain_training", "explain_lab",
        }
        for name in method_names:
            assert callable(getattr(adapter, name))
        assert len(method_names) == len(RobotCommandType)


class TestUnsupportedActionsAreNotExposed:
    """
    Navigation-facing actions such as `show_navigation_step` and
    `show_arrival` are suggested conceptually in the phase brief, but
    app.navigation is an unimplemented placeholder and no existing
    RobotCommandType corresponds to a navigation step or an arrival
    announcement. Per the strict change rules, the adapter must not
    invent unsupported behavior -- these methods must not exist.
    """

    @pytest.mark.parametrize(
        "method_name",
        ["show_navigation_step", "show_arrival"],
    )
    def test_unsupported_conceptual_methods_do_not_exist(self, method_name):
        adapter = RobotIntegrationAdapter()
        assert not hasattr(adapter, method_name)


class TestInputValidation:
    @pytest.fixture()
    def adapter(self) -> RobotIntegrationAdapter:
        return RobotIntegrationAdapter()

    def test_speak_rejects_non_string_non_none_text(self, adapter):
        with pytest.raises(AdapterError):
            adapter.speak(12345)  # type: ignore[arg-type]

    def test_speak_rejects_list_text(self, adapter):
        with pytest.raises(AdapterError):
            adapter.speak(["not", "a", "string"])  # type: ignore[arg-type]

    def test_explain_ai_rejects_non_string_non_none_text(self, adapter):
        with pytest.raises(AdapterError):
            adapter.explain_ai(3.14)  # type: ignore[arg-type]

    def test_speak_none_is_forwarded_and_handled_safely_by_existing_controller(
        self, adapter
    ):
        # None is a legal Optional[str] value for RobotCommand.text --
        # the adapter does not reject it; the existing RobotController
        # already reports it as a safe, non-raising failure.
        result = adapter.speak(None)  # type: ignore[arg-type]
        assert result.success is False

    def test_empty_string_speech_is_forwarded_not_rejected_by_adapter(self, adapter):
        # Content-level validation (empty/whitespace text) belongs to
        # the existing RobotController, not duplicated in the adapter.
        result = adapter.speak("")
        assert isinstance(result, RobotExecutionResult)
        assert result.success is False
        assert "text" in result.message.lower()

    def test_whitespace_only_speech_is_forwarded_not_rejected_by_adapter(self, adapter):
        result = adapter.speak("   ")
        assert result.success is False


class TestBackendFailureHandling:
    def test_backend_failure_is_reported_not_raised(self):
        class FailingBackend(RobotBackend):
            def execute(self, command):
                raise RuntimeError("simulated hardware fault")

        adapter = RobotIntegrationAdapter(
            robot_controller=RobotController(backend=FailingBackend())
        )
        result = adapter.execute_greeting()
        assert result.success is False
        assert "simulated hardware fault" in result.message

    def test_backend_failure_on_explain_is_reported_not_raised(self):
        class FailingBackend(RobotBackend):
            def execute(self, command):
                raise RuntimeError("simulated hardware fault")

        adapter = RobotIntegrationAdapter(
            robot_controller=RobotController(backend=FailingBackend())
        )
        result = adapter.explain_ai("some text")
        assert result.success is False


class TestRobotControllerCompatibility:
    def test_existing_robot_command_type_values_unchanged(self):
        expected = {
            "GREET", "WAVE", "SPEAK", "EXPLAIN_AI", "EXPLAIN_ROBOTICS",
            "EXPLAIN_TRAINING", "EXPLAIN_LAB", "IDLE", "STOP",
        }
        actual = {member.value for member in RobotCommandType}
        assert actual == expected

    def test_adapter_result_matches_direct_controller_call(self):
        # A greeting issued through the adapter must produce a result
        # identical in shape to calling RobotController.greet()
        # directly -- the adapter adds translation, not new behavior.
        direct_result = RobotController().greet()

        adapter = RobotIntegrationAdapter(robot_controller=RobotController())
        adapter_result = adapter.execute_greeting()

        assert adapter_result.command_type == direct_result.command_type
        assert adapter_result.success == direct_result.success

    def test_adapter_reuses_existing_robot_execution_result_type(self):
        # The adapter must not invent its own duplicate result model --
        # it returns the existing RobotExecutionResult directly.
        adapter = RobotIntegrationAdapter()
        result = adapter.execute_greeting()
        assert type(result).__name__ == "RobotExecutionResult"
        assert type(result).__module__ == "app.robot.robot_controller"

    def test_adapter_reaches_the_shared_backend(self):
        backend = SimulatedRobotBackend()
        robot_controller = RobotController(backend=backend)
        adapter = RobotIntegrationAdapter(robot_controller=robot_controller)

        adapter.execute_greeting()
        adapter.wave()

        assert len(backend.history) == 2
        assert backend.history[0].command_type is RobotCommandType.GREET
        assert backend.history[1].command_type is RobotCommandType.WAVE


class TestAdapterDoesNotBypassRobotController:
    def test_adapter_never_constructs_its_own_backend(self):
        import inspect

        source = inspect.getsource(RobotIntegrationAdapter)
        assert "SimulatedRobotBackend(" not in source
        assert "RobotBackend(" not in source

    def test_all_explain_command_types_are_existing_robot_command_types(self):
        for command_type in _EXPLAIN_COMMAND_TYPES:
            assert command_type in RobotCommandType

    def test_internal_explain_rejects_non_explain_command_type(self):
        adapter = RobotIntegrationAdapter()
        with pytest.raises(AdapterError):
            adapter._explain(RobotCommandType.GREET, "text")


class TestHardwareAndNetworkIndependence:
    def test_adapter_operates_without_physical_hardware(self):
        adapter = RobotIntegrationAdapter()
        result = adapter.execute_greeting()
        assert result.success is True

    def test_adapter_files_do_not_import_socket_or_network_modules(self):
        forbidden = {"socket", "serial", "requests", "urllib"}
        for path in (
            "app/integration/__init__.py",
            "app/integration/robot_adapter.py",
        ):
            tree = ast.parse(open(path).read())
            mods = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    mods.add(node.module)
                elif isinstance(node, ast.Import):
                    mods.update(alias.name for alias in node.names)
            assert not (mods & forbidden)


class TestDependencyIsolation:
    ADAPTER_FILES = (
        "app/integration/__init__.py",
        "app/integration/robot_adapter.py",
    )

    def _imported_modules(self, path):
        tree = ast.parse(open(path).read())
        mods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                mods.append(node.module)
            elif isinstance(node, ast.Import):
                mods.extend(alias.name for alias in node.names)
        return mods

    @pytest.mark.parametrize(
        "forbidden_prefix",
        ["app.vision", "app.ml", "app.dl"],
    )
    def test_adapter_never_imports_strictly_forbidden_modules(self, forbidden_prefix):
        for path in self.ADAPTER_FILES:
            mods = self._imported_modules(path)
            assert not any(
                m == forbidden_prefix or m.startswith(forbidden_prefix + ".")
                for m in mods
            ), f"{path} imports forbidden module matching {forbidden_prefix}"

    @pytest.mark.parametrize(
        "avoided_prefix",
        ["app.decision", "app.guide", "app.navigation", "app.main"],
    )
    def test_adapter_avoids_importing_discouraged_modules(self, avoided_prefix):
        for path in self.ADAPTER_FILES:
            mods = self._imported_modules(path)
            assert not any(
                m == avoided_prefix or m.startswith(avoided_prefix + ".")
                for m in mods
            ), f"{path} imports avoided module matching {avoided_prefix}"


class TestNoCircularImports:
    def test_adapter_imports_cleanly_alongside_full_project(self):
        import importlib

        for mod in (
            "app.robot",
            "app.robot.robot_commands",
            "app.robot.robot_controller",
            "app.integration",
            "app.integration.robot_adapter",
            "app.vision",
            "app.decision",
            "app.guide",
            "app.navigation",
            "app.models",
            "app.config",
            "app.utils.logger",
            "app.main",
        ):
            importlib.import_module(mod)


class TestDeterministicBehavior:
    def test_adapter_actions_are_deterministic(self):
        adapter = RobotIntegrationAdapter()
        result1 = adapter.execute_greeting()
        result2 = adapter.execute_greeting()
        assert result1.command_type == result2.command_type
        assert result1.success == result2.success
