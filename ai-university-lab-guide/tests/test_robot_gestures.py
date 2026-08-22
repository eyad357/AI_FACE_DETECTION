"""
Tests for the Robot Gestures phase (app.robot.gesture_definitions /
gesture_mapper / gesture_controller).

These tests require no physical robot, no Robot SDK, no network, no
Vision, no ML, no DL, no Navigation, no Decision, no Guide, and no UI.
`GestureController`'s default backend is `RobotController()`, whose own
default backend is `SimulatedRobotBackend` — deterministic and
hardware-free by design, exactly like the existing Robot tests.
"""

import ast

import pytest

from app.robot.gesture_controller import (
    GestureController,
    GestureExecutionResult,
)
from app.robot.gesture_definitions import (
    GestureError,
    GestureIntent,
    GestureRequest,
    validate_gesture_request,
)
from app.robot.gesture_mapper import (
    GESTURE_TO_ROBOT_COMMAND,
    SUPPORTED_GESTURES,
    UNSUPPORTED_GESTURES,
    is_gesture_supported,
    map_gesture_to_command,
)
from app.robot.robot_commands import RobotCommandType
from app.robot.robot_controller import RobotBackend, RobotController, SimulatedRobotBackend


class TestModuleImports:
    def test_gesture_module_imports_successfully(self):
        assert GestureController is not None
        assert GestureIntent is not None
        assert GestureRequest is not None


class TestGestureVocabulary:
    """
    Pins down the gesture-level vocabulary requested for this phase, so
    it cannot silently drift.
    """

    def test_all_requested_gestures_exist(self):
        expected = {
            "WAVE", "POINT", "ACKNOWLEDGE", "THINKING", "ARRIVED", "IDLE",
        }
        actual = {member.value for member in GestureIntent}
        assert actual == expected

    def test_gesture_values_match_names(self):
        for member in GestureIntent:
            assert member.value == member.name

    def test_every_gesture_has_a_mapping_entry(self):
        # Every GestureIntent must be present in the mapping table,
        # even if its mapping is None (unsupported) -- no gesture is
        # silently forgotten.
        assert set(GESTURE_TO_ROBOT_COMMAND.keys()) == set(GestureIntent)


class TestGestureMapping:
    """
    Verifies the gesture -> existing RobotCommandType mapping without
    ever introducing a new RobotCommandType.
    """

    def test_wave_maps_to_existing_wave_command(self):
        assert map_gesture_to_command(GestureIntent.WAVE) is RobotCommandType.WAVE

    def test_idle_maps_to_existing_idle_command(self):
        assert map_gesture_to_command(GestureIntent.IDLE) is RobotCommandType.IDLE

    @pytest.mark.parametrize(
        "gesture",
        [
            GestureIntent.POINT,
            GestureIntent.ACKNOWLEDGE,
            GestureIntent.THINKING,
            GestureIntent.ARRIVED,
        ],
    )
    def test_gestures_without_a_safe_existing_mapping_are_unsupported(self, gesture):
        assert map_gesture_to_command(gesture) is None
        assert is_gesture_supported(gesture) is False

    def test_supported_and_unsupported_partition_all_gestures(self):
        assert SUPPORTED_GESTURES | UNSUPPORTED_GESTURES == set(GestureIntent)
        assert SUPPORTED_GESTURES & UNSUPPORTED_GESTURES == set()

    def test_supported_gestures_are_wave_and_idle_only(self):
        assert SUPPORTED_GESTURES == {GestureIntent.WAVE, GestureIntent.IDLE}

    def test_mapping_never_invents_a_new_command_type(self):
        # Every non-None value in the mapping table must be a member of
        # the existing, unmodified RobotCommandType enum.
        for command_type in GESTURE_TO_ROBOT_COMMAND.values():
            if command_type is not None:
                assert command_type in RobotCommandType

    def test_map_gesture_to_command_rejects_non_gesture_intent(self):
        with pytest.raises(GestureError):
            map_gesture_to_command("WAVE")  # type: ignore[arg-type]


class TestGestureValidation:
    def test_valid_request_passes_validation(self):
        validate_gesture_request(GestureRequest(GestureIntent.WAVE))

    def test_non_gesture_request_raises_gesture_error(self):
        with pytest.raises(GestureError):
            validate_gesture_request("WAVE")

    def test_none_raises_gesture_error(self):
        with pytest.raises(GestureError):
            validate_gesture_request(None)

    def test_request_with_invalid_gesture_field_raises_gesture_error(self):
        request = GestureRequest.__new__(GestureRequest)
        object.__setattr__(request, "gesture", "not-a-gesture-intent")
        object.__setattr__(request, "text", None)
        object.__setattr__(request, "metadata", {})
        with pytest.raises(GestureError):
            validate_gesture_request(request)


class TestGestureControllerInitialization:
    def test_initializes_with_default_robot_controller(self):
        controller = GestureController()
        assert isinstance(controller._robot_controller, RobotController)
        assert isinstance(controller._robot_controller._backend, SimulatedRobotBackend)

    def test_initializes_with_custom_robot_controller(self):
        robot_controller = RobotController()
        controller = GestureController(robot_controller=robot_controller)
        assert controller._robot_controller is robot_controller


class TestSupportedGestureExecution:
    @pytest.fixture()
    def controller(self) -> GestureController:
        return GestureController()

    def test_wave_gesture_executes_successfully(self, controller):
        result = controller.execute_gesture(GestureRequest(GestureIntent.WAVE))
        assert isinstance(result, GestureExecutionResult)
        assert result.success is True
        assert result.gesture is GestureIntent.WAVE
        assert result.robot_result is not None
        assert result.robot_result.command_type is RobotCommandType.WAVE

    def test_idle_gesture_executes_successfully(self, controller):
        result = controller.execute_gesture(GestureRequest(GestureIntent.IDLE))
        assert result.success is True
        assert result.gesture is GestureIntent.IDLE
        assert result.robot_result.command_type is RobotCommandType.IDLE

    def test_supported_gesture_reaches_the_backend(self):
        backend = SimulatedRobotBackend()
        robot_controller = RobotController(backend=backend)
        controller = GestureController(robot_controller=robot_controller)

        controller.execute_gesture(GestureRequest(GestureIntent.WAVE))

        assert len(backend.history) == 1
        assert backend.history[0].command_type is RobotCommandType.WAVE


class TestUnsupportedGestureHandling:
    @pytest.fixture()
    def controller(self) -> GestureController:
        return GestureController()

    @pytest.mark.parametrize(
        "gesture",
        [
            GestureIntent.POINT,
            GestureIntent.ACKNOWLEDGE,
            GestureIntent.THINKING,
            GestureIntent.ARRIVED,
        ],
    )
    def test_unsupported_gesture_fails_safely_without_raising(self, controller, gesture):
        result = controller.execute_gesture(GestureRequest(gesture))
        assert isinstance(result, GestureExecutionResult)
        assert result.success is False
        assert result.robot_result is None
        assert gesture.value in result.message

    def test_unsupported_gesture_never_reaches_the_backend(self):
        backend = SimulatedRobotBackend()
        robot_controller = RobotController(backend=backend)
        controller = GestureController(robot_controller=robot_controller)

        controller.execute_gesture(GestureRequest(GestureIntent.POINT))

        assert backend.history == []


class TestGestureErrorHandling:
    @pytest.fixture()
    def controller(self) -> GestureController:
        return GestureController()

    def test_invalid_request_type_raises_gesture_error(self, controller):
        with pytest.raises(GestureError):
            controller.execute_gesture("not a gesture request")  # type: ignore[arg-type]

    def test_none_request_raises_gesture_error(self, controller):
        with pytest.raises(GestureError):
            controller.execute_gesture(None)  # type: ignore[arg-type]


class TestGestureSequencing:
    @pytest.fixture()
    def controller(self) -> GestureController:
        return GestureController()

    def test_sequence_executes_in_order(self, controller):
        results = controller.execute_sequence(
            [
                GestureRequest(GestureIntent.WAVE),
                GestureRequest(GestureIntent.IDLE),
            ]
        )
        assert [r.gesture for r in results] == [GestureIntent.WAVE, GestureIntent.IDLE]
        assert all(r.success for r in results)

    def test_sequence_continues_past_unsupported_gestures(self, controller):
        results = controller.execute_sequence(
            [
                GestureRequest(GestureIntent.WAVE),
                GestureRequest(GestureIntent.POINT),
                GestureRequest(GestureIntent.IDLE),
            ]
        )
        assert [r.success for r in results] == [True, False, True]

    def test_empty_sequence_returns_empty_list(self, controller):
        assert controller.execute_sequence([]) == []


class TestBackendIsolationAndDeterminism:
    def test_gesture_layer_does_not_create_own_backend(self):
        # GestureController never talks to a RobotBackend directly --
        # it only holds a RobotController, which owns backend
        # selection.
        import inspect

        source = inspect.getsource(GestureController)
        assert "RobotBackend(" not in source
        assert "SimulatedRobotBackend(" not in source or "def __init__" not in source

    def test_gesture_controller_operates_without_physical_hardware(self):
        controller = GestureController()
        result = controller.execute_gesture(GestureRequest(GestureIntent.WAVE))
        assert result.success is True

    def test_gesture_execution_is_deterministic(self):
        controller = GestureController()
        result1 = controller.execute_gesture(GestureRequest(GestureIntent.WAVE))
        result2 = controller.execute_gesture(GestureRequest(GestureIntent.WAVE))
        assert result1.success == result2.success
        assert result1.gesture == result2.gesture


class TestNoForbiddenImports:
    """
    Verifies the gesture layer only imports what this phase's rules
    allow: the standard library, this phase's own gesture modules, the
    existing app.robot public modules, and app.utils.logger.
    """

    GESTURE_FILES = (
        "app/robot/gesture_definitions.py",
        "app/robot/gesture_mapper.py",
        "app/robot/gesture_controller.py",
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
        ["app.vision", "app.ml", "app.dl", "app.navigation", "app.decision", "app.main"],
    )
    def test_gesture_files_do_not_import_forbidden_modules(self, forbidden_prefix):
        for path in self.GESTURE_FILES:
            mods = self._imported_modules(path)
            assert not any(
                m == forbidden_prefix or m.startswith(forbidden_prefix + ".")
                for m in mods
            ), f"{path} imports forbidden module matching {forbidden_prefix}"

    def test_gesture_files_do_not_import_socket_or_network_modules(self):
        forbidden = {"socket", "serial", "requests", "urllib"}
        for path in self.GESTURE_FILES:
            mods = set(self._imported_modules(path))
            assert not (mods & forbidden)


class TestNoCircularImports:
    def test_gesture_modules_import_cleanly_alongside_full_project(self):
        import importlib

        for mod in (
            "app.robot",
            "app.robot.robot_commands",
            "app.robot.robot_controller",
            "app.robot.gesture_definitions",
            "app.robot.gesture_mapper",
            "app.robot.gesture_controller",
            "app.vision",
            "app.decision",
            "app.guide",
            "app.models",
            "app.config",
            "app.utils.logger",
            "app.main",
        ):
            importlib.import_module(mod)


class TestCompatibilityWithExistingRobotController:
    def test_existing_robot_command_type_values_unchanged(self):
        expected = {
            "GREET", "WAVE", "SPEAK", "EXPLAIN_AI", "EXPLAIN_ROBOTICS",
            "EXPLAIN_TRAINING", "EXPLAIN_LAB", "IDLE", "STOP",
        }
        actual = {member.value for member in RobotCommandType}
        assert actual == expected

    def test_gesture_controller_reuses_existing_robot_controller_execute(self):
        # A gesture that maps to an existing command must produce a
        # RobotExecutionResult identical in shape to what calling
        # RobotController.execute() directly would produce.
        robot_controller = RobotController()
        direct_result = robot_controller.wave()

        gesture_controller = GestureController(robot_controller=RobotController())
        gesture_result = gesture_controller.execute_gesture(
            GestureRequest(GestureIntent.WAVE)
        )

        assert gesture_result.robot_result.command_type == direct_result.command_type
        assert gesture_result.robot_result.success == direct_result.success
