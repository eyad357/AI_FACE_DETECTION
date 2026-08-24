"""
Tests for app.main (ApplicationIntegration).

These tests require no physical camera, no physical robot, no Robot
SDK, no network, and no database. They exercise the full Vision-shaped
DetectionResult -> Decision -> Guide -> Robot pipeline using only
synthetic data and the deterministic SimulatedRobotBackend.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.config import CONFIG
from app.decision.event_manager import ApplicationState, GuideTopic
from app.main import ApplicationIntegration
from app.models.schemas import BoundingBox, DetectionResult, FaceDetection
from app.robot import RobotCommandType, RobotController, SimulatedRobotBackend

BASE_TIME = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_result(face_count: int, t: datetime = BASE_TIME) -> DetectionResult:
    if face_count == 0:
        return DetectionResult.empty(timestamp=t)
    faces = [
        FaceDetection(bounding_box=BoundingBox(x=i * 10, y=0, width=20, height=20))
        for i in range(face_count)
    ]
    return DetectionResult(
        detected=True,
        face_count=face_count,
        confidence=None,
        timestamp=t,
        faces=faces,
    )


def frames_required() -> int:
    return CONFIG.vision.detection_frames_required


def drive_to_greeting(app: ApplicationIntegration, start: datetime = BASE_TIME):
    t = start
    results = []
    for i in range(frames_required()):
        t = start + timedelta(seconds=i)
        results = app.handle_detection(make_result(1, t))
    return t, results


class TestInitialization:
    def test_application_integration_initializes(self):
        app = ApplicationIntegration()
        assert app is not None
        assert app.state_manager.state is ApplicationState.WAITING

    def test_initializes_with_injected_dependencies(self):
        from app.decision.state_manager import StateManager
        from app.guide import GuideService

        state_manager = StateManager()
        guide_service = GuideService()
        robot_controller = RobotController()
        app = ApplicationIntegration(
            state_manager=state_manager,
            guide_service=guide_service,
            robot_controller=robot_controller,
        )
        assert app.state_manager is state_manager


class TestVisionToDecisionContract:
    def test_detection_result_reaches_decision(self):
        app = ApplicationIntegration()
        t, _ = drive_to_greeting(app)
        assert app.state_manager.state is ApplicationState.GREETING

    def test_real_face_detector_output_is_compatible(self):
        # Uses Vision's actual FaceDetector on a synthetic (blank) frame
        # -- no camera hardware required -- to prove the real
        # DetectionResult contract produced by Vision is exactly what
        # Decision (and therefore ApplicationIntegration) consumes.
        import numpy as np

        from app.vision.face_detector import FaceDetector

        detector = FaceDetector()
        frame = np.zeros((200, 200, 3), dtype=np.uint8)
        detection_result = detector.detect(frame)

        app = ApplicationIntegration()
        results = app.handle_detection(detection_result)
        assert isinstance(results, list)
        assert app.state_manager.state is ApplicationState.WAITING


class TestGreetingDispatch:
    def test_greeting_required_dispatches_greet_command(self):
        app = ApplicationIntegration()
        t, results = drive_to_greeting(app)
        assert len(results) == 1
        assert results[0].command_type is RobotCommandType.GREET
        assert results[0].success is True

    def test_robot_history_records_greet(self):
        backend = SimulatedRobotBackend()
        app = ApplicationIntegration(robot_controller=RobotController(backend=backend))
        drive_to_greeting(app)
        assert any(
            cmd.command_type is RobotCommandType.GREET for cmd in backend.history
        )


class TestGuideDispatch:
    def test_explanation_reaches_guide_service(self):
        app = ApplicationIntegration()
        t, _ = drive_to_greeting(app)
        app.complete_greeting()
        results = app.select_topic(GuideTopic.ROBOTICS)
        assert len(results) == 1
        assert results[0].command_type is RobotCommandType.EXPLAIN_ROBOTICS
        assert results[0].success is True

    def test_guide_response_spoken_text_reaches_robot(self):
        backend = SimulatedRobotBackend()
        app = ApplicationIntegration(robot_controller=RobotController(backend=backend))
        drive_to_greeting(app)
        app.complete_greeting()
        app.select_topic(GuideTopic.AI_PROJECTS)

        explain_commands = [
            cmd for cmd in backend.history if cmd.command_type is RobotCommandType.EXPLAIN_AI
        ]
        assert len(explain_commands) == 1
        assert explain_commands[0].text is not None
        assert explain_commands[0].text.strip() != ""

    def test_all_topics_map_to_correct_robot_command(self):
        expected = {
            GuideTopic.AI_PROJECTS: RobotCommandType.EXPLAIN_AI,
            GuideTopic.ROBOTICS: RobotCommandType.EXPLAIN_ROBOTICS,
            GuideTopic.TRAINING: RobotCommandType.EXPLAIN_TRAINING,
            GuideTopic.LAB_INFORMATION: RobotCommandType.EXPLAIN_LAB,
        }
        for topic, expected_command in expected.items():
            app = ApplicationIntegration()
            drive_to_greeting(app)
            app.complete_greeting()
            results = app.select_topic(topic)
            assert len(results) == 1
            assert results[0].command_type is expected_command


class TestSessionCompletionAndCooldown:
    def test_complete_session_dispatches_idle(self):
        app = ApplicationIntegration()
        drive_to_greeting(app)
        app.complete_greeting()
        app.select_topic(GuideTopic.TRAINING)
        results = app.complete_session()
        assert any(r.command_type is RobotCommandType.IDLE for r in results)
        assert app.state_manager.state is ApplicationState.COOLDOWN


class TestRobotResultHandling:
    def test_robot_execution_result_is_returned(self):
        app = ApplicationIntegration()
        t, results = drive_to_greeting(app)
        for r in results:
            assert hasattr(r, "success")
            assert hasattr(r, "message")
            assert hasattr(r, "command_type")

    def test_robot_failure_does_not_corrupt_decision_state(self):
        from app.robot import RobotBackend

        class FailingBackend(RobotBackend):
            def execute(self, command):
                raise RuntimeError("simulated robot fault")

        app = ApplicationIntegration(
            robot_controller=RobotController(backend=FailingBackend())
        )
        t, results = drive_to_greeting(app)
        # RobotController itself catches backend exceptions and returns
        # a success=False result -- Decision's state must still have
        # advanced normally.
        assert app.state_manager.state is ApplicationState.GREETING
        assert len(results) == 1
        assert results[0].success is False


class TestUnsupportedEventsHandledSafely:
    def test_no_visitor_produces_no_robot_command(self):
        app = ApplicationIntegration()
        results = app.handle_detection(make_result(0, BASE_TIME))
        # NO_VISITOR is informational only -- no RobotCommandType maps to it.
        assert results == []

    def test_multiple_visitors_informational_event_produces_no_extra_command(self):
        app = ApplicationIntegration()
        results = app.handle_detection(make_result(3, BASE_TIME))
        # MULTIPLE_VISITORS itself dispatches nothing (only stability-gated
        # GREETING_REQUIRED would, once reached).
        assert results == []

    def test_invalid_detection_result_handled_safely(self):
        app = ApplicationIntegration()
        results = app.handle_detection(None)  # type: ignore[arg-type]
        # StateManager converts this to an ERROR event; main.py maps
        # ERROR -> STOP.
        assert len(results) == 1
        assert results[0].command_type is RobotCommandType.STOP
        assert app.state_manager.state is ApplicationState.ERROR

    def test_reset_recovers_from_error(self):
        app = ApplicationIntegration()
        app.handle_detection(None)  # type: ignore[arg-type]
        assert app.state_manager.state is ApplicationState.ERROR
        app.reset()
        assert app.state_manager.state is ApplicationState.WAITING


class TestCaptureAndHandleWithoutHardware:
    def test_capture_and_handle_without_camera_returns_empty(self):
        app = ApplicationIntegration()  # no camera/detector configured
        results = app.capture_and_handle()
        assert results == []

    def test_capture_and_handle_with_unavailable_camera_returns_empty(self):
        from app.vision.camera import Camera
        from app.vision.face_detector import FaceDetector

        # Index guaranteed absent on any dev/CI machine -- proves this
        # path requires no real hardware and fails gracefully.
        camera = Camera(index=9999)
        detector = FaceDetector()
        app = ApplicationIntegration(camera=camera, detector=detector)
        results = app.capture_and_handle()
        assert results == []


class TestHardwareIndependence:
    def test_full_flow_runs_without_hardware(self):
        app = ApplicationIntegration()
        drive_to_greeting(app)
        app.complete_greeting()
        app.select_topic(GuideTopic.LAB_INFORMATION)
        app.complete_session()
        assert app.state_manager.state is ApplicationState.COOLDOWN


class TestDependencyIsolation:
    def test_main_module_is_the_only_place_wiring_everything(self):
        import ast

        tree = ast.parse(open("app/main.py").read())
        mods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                mods.append(node.module)
            elif isinstance(node, ast.Import):
                mods.extend(a.name for a in node.names)

        assert any(m.startswith("app.decision") for m in mods)
        assert any(m.startswith("app.guide") for m in mods)
        assert any(m.startswith("app.robot") for m in mods)
        assert any(m.startswith("app.vision") for m in mods)

    def test_vision_does_not_import_robot(self):
        import ast

        for f in (
            "app/vision/camera.py",
            "app/vision/detector_interface.py",
            "app/vision/face_detector.py",
        ):
            tree = ast.parse(open(f).read())
            mods = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    mods.append(node.module)
                elif isinstance(node, ast.Import):
                    mods.extend(a.name for a in node.names)
            assert not any(m.startswith("app.robot") for m in mods)

    def test_robot_does_not_import_vision(self):
        import ast

        for f in (
            "app/robot/robot_commands.py",
            "app/robot/robot_controller.py",
        ):
            tree = ast.parse(open(f).read())
            mods = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    mods.append(node.module)
                elif isinstance(node, ast.Import):
                    mods.extend(a.name for a in node.names)
            assert not any(m.startswith("app.vision") for m in mods)

    def test_guide_does_not_import_robot(self):
        import ast

        for f in ("app/guide/guide_service.py", "app/guide/content.py"):
            tree = ast.parse(open(f).read())
            mods = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    mods.append(node.module)
                elif isinstance(node, ast.Import):
                    mods.extend(a.name for a in node.names)
            assert not any(m.startswith("app.robot") for m in mods)

    def test_robot_does_not_import_guide(self):
        import ast

        for f in ("app/robot/robot_commands.py", "app/robot/robot_controller.py"):
            tree = ast.parse(open(f).read())
            mods = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    mods.append(node.module)
                elif isinstance(node, ast.Import):
                    mods.extend(a.name for a in node.names)
            assert not any(m.startswith("app.guide") for m in mods)

    def test_no_circular_imports(self):
        import importlib

        for mod in (
            "app.main",
            "app.vision",
            "app.decision",
            "app.guide",
            "app.robot",
            "app.models",
            "app.config",
            "app.utils.logger",
        ):
            importlib.import_module(mod)
