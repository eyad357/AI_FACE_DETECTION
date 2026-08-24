"""
Tests for app.ui.adapters.vision_adapter.VisionAdapter.

Requires no physical camera. In a headless environment the adapter
must report an honest unavailable state rather than fabricating a
detection.
"""

from __future__ import annotations

from app.ui.adapters.vision_adapter import VisionAdapter
from app.ui.dashboard_view_models import HealthState


class TestVisionAdapter:
    def test_status_never_raises(self):
        adapter = VisionAdapter()
        status = adapter.status()
        assert status.name == "Vision"
        assert isinstance(status.state, HealthState)

    def test_capture_and_detect_never_raises_without_camera(self):
        adapter = VisionAdapter()
        view = adapter.capture_and_detect()
        # Either a real capture happened, or camera_available is False
        # with an honest reason -- never a fabricated detection.
        if not view.camera_available:
            assert view.unavailable_reason
            assert view.detected is None
