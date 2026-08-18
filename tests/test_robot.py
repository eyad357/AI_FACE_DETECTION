"""
Tests for app.robot (RobotCommand / RobotController / SimulatedRobotBackend).

These tests require no physical robot, no Robot SDK, no network, no
Vision, no Camera, no Decision, no Guide, and no UI. RobotController's
default backend (SimulatedRobotBackend) is deterministic and
hardware-free by design.
"""

import pytest

from app.robot import (
    RobotBackend,
    RobotCommand,
    RobotCommandType,
    RobotController,
    RobotError,
    RobotExecutionResult,
    SimulatedRobotBackend,
)


class TestModuleImports:
    def test_robot_module_imports_successfully(self):
        assert RobotController is not None
        assert RobotCommand is not None
        assert RobotCommandType is not None


class TestRobotControllerInitialization:
    def test_initializes_with_default_backend(self):
        controller = RobotController()
        assert isinstance(controller._backend, SimulatedRobotBackend)

    def test_initializes_with_custom_backend(self):
        backend = SimulatedRobotBackend()
        controller = RobotController(backend=backend)
        assert controller._backend is backend


class TestExistingRobotCommandsPreserved:
    """
    Pins down the exact command vocabulary documented back in Phase 1,
    so it cannot silently drift.
    """

    def test_all_phase1_documented_commands_exist(self):
        expected = {
            "GREET", "WAVE", "SPEAK", "EXPLAIN_AI", "EXPLAIN_ROBOTICS",
            "EXPLAIN_TRAINING", "EXPLAIN_LAB", "IDLE", "STOP",
        }
        actual = {member.value for member in RobotCommandType}
        assert actual == expected

    def test_command_values_match_names(self):
        # Values are the same strings as the enum member names -- no
        # silent renaming.
        for member in RobotCommandType:
            assert member.value == member.name


class TestCoreCommandExecution:
    @pytest.fixture()
    def controller(self) -> RobotController:
        return RobotController()

    def test_greet_executes_successfully(self, controller):
        result = controller.greet()
        assert isinstance(result, RobotExecutionResult)
        assert result.success is True
        assert result.command_type is RobotCommandType.GREET

    def test_wave_executes_successfully(self, controller):
        result = controller.wave()
        assert result.success is True
        assert result.command_type is RobotCommandType.WAVE

    def test_speak_executes_successfully(self, controller):
        result = controller.speak("Welcome to the lab.")
        assert result.success is True
        assert result.command_type is RobotCommandType.SPEAK

    def test_stop_executes_successfully(self, controller):
        result = controller.stop()
        assert result.success is True
        assert result.command_type is RobotCommandType.STOP

    def test_idle_executes_successfully(self, controller):
        result = controller.idle()
        assert result.success is True
        assert result.command_type is RobotCommandType.IDLE

    def test_explain_commands_execute_with_text(self, controller):
        for topic_command in (
            RobotCommandType.EXPLAIN_AI,
            RobotCommandType.EXPLAIN_ROBOTICS,
            RobotCommandType.EXPLAIN_TRAINING,
            RobotCommandType.EXPLAIN_LAB,
        ):
            result = controller.execute(
                RobotCommand(topic_command, text="some explanation text")
            )
            assert result.success is True
            assert result.command_type is topic_command


class TestErrorHandling:
    @pytest.fixture()
    def controller(self) -> RobotController:
        return RobotController()

    def test_invalid_command_type_raises_robot_error(self, controller):
        with pytest.raises(RobotError):
            controller.execute("not a command")  # type: ignore[arg-type]

    def test_invalid_command_type_none_raises_robot_error(self, controller):
        with pytest.raises(RobotError):
            controller.execute(None)  # type: ignore[arg-type]

    def test_empty_speech_handled_safely(self, controller):
        result = controller.speak("")
        assert isinstance(result, RobotExecutionResult)
        assert result.success is False
        assert "text" in result.message.lower()

    def test_whitespace_only_speech_handled_safely(self, controller):
        result = controller.speak("   ")
        assert result.success is False

    def test_none_speech_text_handled_safely(self, controller):
        result = controller.execute(RobotCommand(RobotCommandType.SPEAK, text=None))
        assert result.success is False

    def test_non_speech_command_does_not_require_text(self, controller):
        # GREET/WAVE/IDLE/STOP never require text.
        result = controller.execute(RobotCommand(RobotCommandType.GREET))
        assert result.success is True

    def test_backend_failure_is_reported_not_raised(self):
        class FailingBackend(RobotBackend):
            def execute(self, command):
                raise RuntimeError("simulated hardware fault")

        controller = RobotController(backend=FailingBackend())
        result = controller.greet()
        assert result.success is False
        assert "simulated hardware fault" in result.message


class TestHardwareIndependence:
    def test_robot_operates_without_physical_hardware(self):
        # RobotController() with no arguments must work everywhere,
        # including CI, with zero hardware/network/SDK involved.
        controller = RobotController()
        result = controller.greet()
        assert result.success is True

    def test_simulated_backend_does_not_touch_network_or_hardware(self):
        import ast

        import app.robot.robot_controller as mod

        tree = ast.parse(open(mod.__file__).read())
        mods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                mods.append(node.module)
            elif isinstance(node, ast.Import):
                mods.extend(a.name for a in node.names)
        forbidden = {"socket", "serial", "requests", "urllib"}
        assert not (set(mods) & forbidden)


class TestDeterministicBehavior:
    def test_commands_are_deterministic(self):
        controller = RobotController()
        result1 = controller.greet()
        result2 = controller.greet()
        assert result1.command_type == result2.command_type
        assert result1.success == result2.success

    def test_simulated_backend_records_history(self):
        backend = SimulatedRobotBackend()
        controller = RobotController(backend=backend)
        controller.greet()
        controller.wave()
        assert len(backend.history) == 2
        assert backend.history[0].command_type is RobotCommandType.GREET
        assert backend.history[1].command_type is RobotCommandType.WAVE


class TestConfigAndLoggerUsage:
    def test_robot_uses_existing_logger(self):
        import ast

        for f in ("app/robot/robot_controller.py", "app/robot/robot_commands.py"):
            tree = ast.parse(open(f).read())
            mods = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    mods.append(node.module)
            assert "logging" not in mods or f.endswith("robot_commands.py")
        import app.robot.robot_controller as mod

        source = open(mod.__file__).read()
        assert "from app.utils.logger import get_logger" in source

    def test_robot_does_not_create_own_config_system(self):
        import pathlib

        robot_dir = pathlib.Path("app/robot")
        config_like_files = [
            f for f in robot_dir.iterdir() if "config" in f.name.lower()
        ]
        assert config_like_files == []


class TestIndependence:
    def test_robot_does_not_import_vision(self):
        import ast

        for f in (
            "app/robot/robot_controller.py",
            "app/robot/robot_commands.py",
            "app/robot/__init__.py",
        ):
            tree = ast.parse(open(f).read())
            mods = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    mods.append(node.module)
                elif isinstance(node, ast.Import):
                    mods.extend(a.name for a in node.names)
            assert not any(m.startswith("app.vision") for m in mods)

    def test_robot_does_not_import_decision(self):
        import ast

        for f in (
            "app/robot/robot_controller.py",
            "app/robot/robot_commands.py",
            "app/robot/__init__.py",
        ):
            tree = ast.parse(open(f).read())
            mods = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    mods.append(node.module)
                elif isinstance(node, ast.Import):
                    mods.extend(a.name for a in node.names)
            assert not any(m.startswith("app.decision") for m in mods)

    def test_robot_does_not_import_guide(self):
        import ast

        for f in (
            "app/robot/robot_controller.py",
            "app/robot/robot_commands.py",
            "app/robot/__init__.py",
        ):
            tree = ast.parse(open(f).read())
            mods = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    mods.append(node.module)
                elif isinstance(node, ast.Import):
                    mods.extend(a.name for a in node.names)
            assert not any(m.startswith("app.guide") for m in mods)

    def test_robot_does_not_import_main(self):
        import ast

        for f in (
            "app/robot/robot_controller.py",
            "app/robot/robot_commands.py",
            "app/robot/__init__.py",
        ):
            tree = ast.parse(open(f).read())
            mods = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    mods.append(node.module)
                elif isinstance(node, ast.Import):
                    mods.extend(a.name for a in node.names)
            assert not any(m == "app.main" or m.startswith("app.main") for m in mods)

    def test_robot_does_not_modify_vision_contracts(self):
        # Robot never imports Vision at all (verified elsewhere), so it
        # cannot construct or reference DetectionResult/FaceDetection/
        # BoundingBox as real names in code -- only as prose in
        # docstrings explaining the boundary, which is fine.
        import ast

        for f in (
            "app/robot/robot_controller.py",
            "app/robot/robot_commands.py",
        ):
            tree = ast.parse(open(f).read())
            names_used = {
                node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
            }
            forbidden = {"DetectionResult", "FaceDetection", "BoundingBox"}
            assert not (names_used & forbidden)

    def test_robot_runs_independently_of_everything_else(self):
        # No Vision, Decision, Guide, UI, camera, or database touched at
        # any point in this test module.
        controller = RobotController()
        result = controller.execute(RobotCommand(RobotCommandType.STOP))
        assert result.success is True


class TestNoCircularImports:
    def test_full_project_imports_cleanly(self):
        import importlib

        for mod in (
            "app.robot",
            "app.robot.robot_commands",
            "app.robot.robot_controller",
            "app.vision",
            "app.decision",
            "app.guide",
            "app.models",
            "app.config",
            "app.utils.logger",
            "app.main",
        ):
            importlib.import_module(mod)
