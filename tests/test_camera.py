"""
Tests for app.vision.camera.Camera.

These tests do NOT require a physical camera to be connected — they
exercise the class's behavior with whatever camera devices are (or are
not) available in the environment, and check that failure modes are
handled gracefully rather than raising.
"""

from app.vision.camera import Camera


class TestCameraInitialization:
    def test_default_construction(self):
        camera = Camera()
        assert camera.is_opened is False

    def test_custom_construction(self):
        camera = Camera(index=99, width=320, height=240)
        assert camera._index == 99
        assert camera._width == 320
        assert camera._height == 240


class TestCameraInvalidDevice:
    def test_opening_invalid_index_does_not_raise(self):
        # A very large index should not correspond to a real device on
        # any CI/dev machine, so this exercises the "camera unavailable"
        # path without needing real hardware.
        camera = Camera(index=9999)
        opened = camera.open()
        assert opened is False
        assert camera.is_opened is False

    def test_read_before_open_is_safe(self):
        camera = Camera(index=9999)
        ok, frame = camera.read()
        assert ok is False
        assert frame is None

    def test_read_after_failed_open_is_safe(self):
        camera = Camera(index=9999)
        camera.open()
        ok, frame = camera.read()
        assert ok is False
        assert frame is None


class TestCameraResourceRelease:
    def test_release_without_open_does_not_raise(self):
        camera = Camera(index=9999)
        camera.release()  # should not raise
        assert camera.is_opened is False

    def test_release_is_idempotent(self):
        camera = Camera(index=9999)
        camera.open()
        camera.release()
        camera.release()  # calling twice should be safe
        assert camera.is_opened is False

    def test_context_manager_releases(self):
        with Camera(index=9999) as camera:
            assert camera.is_opened in (True, False)
        assert camera.is_opened is False
