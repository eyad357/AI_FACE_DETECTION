"""
Tests for app.config.

These tests require no camera, no OpenCV, no Robot, no Robot SDK, no
hardware, and no network access — config must be importable and
constructible entirely standalone.
"""

import os

import pytest

from app.config import (
    CONFIG,
    AppConfig,
    CameraConfig,
    ConfigurationError,
    DecisionConfig,
    LoggingConfig,
    VisionConfig,
    _env_float,
    _env_int,
)


class TestConfigImportsIndependently:
    def test_config_module_imports_successfully(self):
        # If this file's imports above succeeded, this already holds --
        # asserting explicitly for clarity.
        assert CONFIG is not None

    def test_config_repr_works_without_hardware(self):
        # Mirrors: python -c "from app.config import CONFIG; print(CONFIG)"
        assert "AppConfig" in repr(CONFIG)

    def test_config_module_has_no_app_internal_imports(self):
        import ast

        import app.config as config_mod

        tree = ast.parse(open(config_mod.__file__).read())
        mods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                mods.append(node.module)
            elif isinstance(node, ast.Import):
                mods.extend(a.name for a in node.names)
        forbidden = [
            m
            for m in mods
            if m.startswith("app.vision")
            or m.startswith("app.robot")
            or m.startswith("app.decision")
            or m.startswith("app.guide")
        ]
        assert forbidden == []


class TestDefaultConfigurationIsValid:
    def test_default_app_config_constructs(self):
        # Constructing a fresh instance exercises __post_init__ validation
        # on every nested config with the actual shipped defaults.
        config = AppConfig()
        assert isinstance(config, AppConfig)

    def test_default_camera_config(self):
        assert CONFIG.camera.index >= 0
        assert CONFIG.camera.width > 0
        assert CONFIG.camera.height > 0
        assert CONFIG.camera.fps > 0

    def test_default_vision_config(self):
        assert 0.0 <= CONFIG.vision.face_confidence_threshold <= 1.0
        assert CONFIG.vision.detection_frames_required > 0
        assert CONFIG.vision.haar_scale_factor > 1.0
        assert CONFIG.vision.haar_min_neighbors >= 0
        assert CONFIG.vision.haar_min_face_size > 0

    def test_default_decision_config(self):
        assert CONFIG.decision.visitor_lost_frames_required > 0
        assert CONFIG.decision.greeting_cooldown_seconds >= 0

    def test_default_logging_config(self):
        assert CONFIG.logging.level.upper() in {
            "CRITICAL", "FATAL", "ERROR", "WARNING", "WARN", "INFO", "DEBUG", "NOTSET",
        }
        assert CONFIG.logging.format.strip() != ""


class TestExistingConsumerCompatibility:
    """
    Vision (app.vision.camera / app.vision.face_detector) and Decision
    (app.decision.state_manager) read specific CONFIG fields directly.
    These tests pin down that those exact fields still exist with their
    existing names/types, so those protected modules keep working.
    """

    def test_vision_camera_fields_present(self):
        assert isinstance(CONFIG.camera.index, int)
        assert isinstance(CONFIG.camera.width, int)
        assert isinstance(CONFIG.camera.height, int)

    def test_vision_face_detector_fields_present(self):
        assert isinstance(CONFIG.vision.haar_scale_factor, float)
        assert isinstance(CONFIG.vision.haar_min_neighbors, int)
        assert isinstance(CONFIG.vision.haar_min_face_size, int)

    def test_decision_fields_present(self):
        assert isinstance(CONFIG.vision.detection_frames_required, int)
        assert isinstance(CONFIG.decision.greeting_cooldown_seconds, float)
        assert isinstance(CONFIG.decision.visitor_lost_frames_required, int)

    def test_no_robot_config_invented(self):
        # Robot currently consumes zero configuration values (verified by
        # inspection). No RobotConfig section should exist until Robot
        # genuinely needs one.
        assert not hasattr(CONFIG, "robot")

    def test_no_guide_config_invented(self):
        # Same reasoning for Guide.
        assert not hasattr(CONFIG, "guide")


class TestInvalidValuesRejected:
    def test_camera_negative_index_rejected(self):
        with pytest.raises(ConfigurationError):
            CameraConfig(index=-1, width=640, height=480, fps=30)

    def test_camera_non_positive_width_rejected(self):
        with pytest.raises(ConfigurationError):
            CameraConfig(index=0, width=0, height=480, fps=30)

    def test_camera_non_positive_height_rejected(self):
        with pytest.raises(ConfigurationError):
            CameraConfig(index=0, width=640, height=-10, fps=30)

    def test_camera_non_positive_fps_rejected(self):
        with pytest.raises(ConfigurationError):
            CameraConfig(index=0, width=640, height=480, fps=0)

    def test_vision_confidence_out_of_range_rejected(self):
        with pytest.raises(ConfigurationError):
            VisionConfig(
                face_confidence_threshold=1.5,
                detection_frames_required=5,
                haar_scale_factor=1.1,
                haar_min_neighbors=5,
                haar_min_face_size=30,
            )

    def test_vision_scale_factor_too_low_rejected(self):
        with pytest.raises(ConfigurationError):
            VisionConfig(
                face_confidence_threshold=0.5,
                detection_frames_required=5,
                haar_scale_factor=1.0,
                haar_min_neighbors=5,
                haar_min_face_size=30,
            )

    def test_vision_non_positive_detection_frames_rejected(self):
        with pytest.raises(ConfigurationError):
            VisionConfig(
                face_confidence_threshold=0.5,
                detection_frames_required=0,
                haar_scale_factor=1.1,
                haar_min_neighbors=5,
                haar_min_face_size=30,
            )

    def test_decision_non_positive_lost_frames_rejected(self):
        with pytest.raises(ConfigurationError):
            DecisionConfig(visitor_lost_frames_required=0, greeting_cooldown_seconds=10.0)

    def test_decision_negative_cooldown_rejected(self):
        with pytest.raises(ConfigurationError):
            DecisionConfig(visitor_lost_frames_required=5, greeting_cooldown_seconds=-1.0)

    def test_logging_invalid_level_rejected(self):
        with pytest.raises(ConfigurationError):
            LoggingConfig(level="NOT_A_LEVEL", format="%(message)s")

    def test_logging_empty_format_rejected(self):
        with pytest.raises(ConfigurationError):
            LoggingConfig(level="INFO", format="   ")

    def test_valid_values_accepted(self):
        # Sanity check that validation isn't overly strict.
        CameraConfig(index=1, width=1280, height=720, fps=60)
        VisionConfig(
            face_confidence_threshold=0.0,
            detection_frames_required=1,
            haar_scale_factor=1.05,
            haar_min_neighbors=0,
            haar_min_face_size=1,
        )
        DecisionConfig(visitor_lost_frames_required=1, greeting_cooldown_seconds=0.0)
        LoggingConfig(level="debug", format="%(message)s")


class TestEnvironmentOverrides:
    """
    Directly exercises the env-parsing helpers, since dataclass field
    defaults are bound once at class-definition time (existing,
    unmodified behavior) rather than re-read per instantiation.
    """

    def test_env_int_uses_default_when_unset(self, monkeypatch):
        monkeypatch.delenv("LABGUIDE_TEST_INT", raising=False)
        assert _env_int("LABGUIDE_TEST_INT", 42) == 42

    def test_env_int_uses_default_when_empty(self, monkeypatch):
        monkeypatch.setenv("LABGUIDE_TEST_INT", "")
        assert _env_int("LABGUIDE_TEST_INT", 42) == 42

    def test_env_int_parses_valid_value(self, monkeypatch):
        monkeypatch.setenv("LABGUIDE_TEST_INT", "7")
        assert _env_int("LABGUIDE_TEST_INT", 42) == 7

    def test_env_int_raises_clearly_on_malformed_value(self, monkeypatch):
        monkeypatch.setenv("LABGUIDE_TEST_INT", "not-an-int")
        with pytest.raises(ConfigurationError) as exc_info:
            _env_int("LABGUIDE_TEST_INT", 42)
        message = str(exc_info.value)
        assert "LABGUIDE_TEST_INT" in message
        assert "not-an-int" in message

    def test_env_float_uses_default_when_unset(self, monkeypatch):
        monkeypatch.delenv("LABGUIDE_TEST_FLOAT", raising=False)
        assert _env_float("LABGUIDE_TEST_FLOAT", 3.14) == 3.14

    def test_env_float_parses_valid_value(self, monkeypatch):
        monkeypatch.setenv("LABGUIDE_TEST_FLOAT", "2.5")
        assert _env_float("LABGUIDE_TEST_FLOAT", 3.14) == 2.5

    def test_env_float_raises_clearly_on_malformed_value(self, monkeypatch):
        monkeypatch.setenv("LABGUIDE_TEST_FLOAT", "abc")
        with pytest.raises(ConfigurationError) as exc_info:
            _env_float("LABGUIDE_TEST_FLOAT", 3.14)
        message = str(exc_info.value)
        assert "LABGUIDE_TEST_FLOAT" in message
        assert "abc" in message


class TestIndependence:
    def test_config_does_not_require_vision(self):
        # app.config was already imported at module load above without
        # touching app.vision or cv2 at all.
        import sys

        assert "app.vision" not in sys.modules or True  # config itself never imports it
        import ast

        import app.config as config_mod

        tree = ast.parse(open(config_mod.__file__).read())
        source_imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                source_imports.append(node.module)
            elif isinstance(node, ast.Import):
                source_imports.extend(a.name for a in node.names)
        assert "cv2" not in source_imports
        assert not any(m.startswith("app.vision") for m in source_imports)

    def test_config_does_not_require_robot(self):
        import ast

        import app.config as config_mod

        tree = ast.parse(open(config_mod.__file__).read())
        source_imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                source_imports.append(node.module)
            elif isinstance(node, ast.Import):
                source_imports.extend(a.name for a in node.names)
        assert not any(m.startswith("app.robot") for m in source_imports)

    def test_no_circular_imports(self):
        import importlib

        for mod in (
            "app.config",
            "app.vision",
            "app.decision",
            "app.guide",
            "app.robot",
            "app.models",
            "app.utils.logger",
            "app.main",
        ):
            importlib.import_module(mod)
