"""
Tests for app.vision.face_detector.FaceDetector.

These tests do not require a physical camera. Most use synthetically
generated NumPy arrays as frames. Tests that require a genuine photo of
a human face (to exercise real positive detections / multi-face
scenarios) are skipped automatically when the corresponding fixture
image is not present — see tests/fixtures/README.md.
"""

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

from app.models.schemas import DetectionResult
from app.vision.detector_interface import FaceDetectorInterface
from app.vision.face_detector import FaceDetector

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
SINGLE_FACE_FIXTURE = FIXTURES_DIR / "single_face.jpg"
MULTI_FACE_FIXTURE = FIXTURES_DIR / "multi_face.jpg"


@pytest.fixture(scope="module")
def detector() -> FaceDetector:
    return FaceDetector()


def _blank_frame(width: int = 200, height: int = 200) -> np.ndarray:
    """A synthetic frame containing no face-like structure."""
    return np.zeros((height, width, 3), dtype=np.uint8)


class TestDetectorInitialization:
    def test_implements_interface(self, detector):
        assert isinstance(detector, FaceDetectorInterface)

    def test_invalid_cascade_path_raises(self):
        with pytest.raises(RuntimeError):
            FaceDetector(cascade_path="/nonexistent/path/to/cascade.xml")


class TestNoFaceFrame:
    def test_blank_frame_returns_no_detection(self, detector):
        result = detector.detect(_blank_frame())
        assert isinstance(result, DetectionResult)
        assert result.detected is False
        assert result.face_count == 0
        assert result.faces == []
        assert result.confidence is None

    def test_grayscale_blank_frame_is_accepted(self, detector):
        frame = np.zeros((200, 200), dtype=np.uint8)
        result = detector.detect(frame)
        assert result.detected is False


class TestDetectionResultStructure:
    def test_result_has_timestamp(self, detector):
        result = detector.detect(_blank_frame())
        assert isinstance(result.timestamp, datetime)

    def test_result_face_count_matches_faces_length(self, detector):
        result = detector.detect(_blank_frame())
        assert result.face_count == len(result.faces)


class TestInvalidInputHandling:
    def test_none_frame_raises(self, detector):
        with pytest.raises(ValueError):
            detector.detect(None)

    def test_non_array_frame_raises(self, detector):
        with pytest.raises(ValueError):
            detector.detect("not an image")

    def test_empty_array_raises(self, detector):
        with pytest.raises(ValueError):
            detector.detect(np.array([]))

    def test_wrong_dimensionality_raises(self, detector):
        with pytest.raises(ValueError):
            detector.detect(np.zeros((10,), dtype=np.uint8))  # 1D
        with pytest.raises(ValueError):
            detector.detect(np.zeros((5, 5, 5, 3), dtype=np.uint8))  # 4D

    def test_unsupported_channel_count_raises(self, detector):
        with pytest.raises(ValueError):
            detector.detect(np.zeros((10, 10, 2), dtype=np.uint8))


@pytest.mark.skipif(
    not SINGLE_FACE_FIXTURE.exists(),
    reason=(
        "Requires tests/fixtures/single_face.jpg — a real photo of a "
        "single human face. See tests/fixtures/README.md."
    ),
)
class TestSingleFaceFixture:
    def test_detects_one_face(self, detector):
        import cv2

        frame = cv2.imread(str(SINGLE_FACE_FIXTURE))
        result = detector.detect(frame)
        assert result.detected is True
        assert result.face_count == 1
        assert result.faces[0].bounding_box.width > 0
        assert result.faces[0].bounding_box.height > 0
        # Haar cascades do not provide a true confidence score.
        assert result.faces[0].confidence is None


@pytest.mark.skipif(
    not MULTI_FACE_FIXTURE.exists(),
    reason=(
        "Requires tests/fixtures/multi_face.jpg — a real photo "
        "containing multiple human faces. See tests/fixtures/README.md."
    ),
)
class TestMultiFaceFixture:
    def test_detects_multiple_faces(self, detector):
        import cv2

        frame = cv2.imread(str(MULTI_FACE_FIXTURE))
        result = detector.detect(frame)
        assert result.detected is True
        assert result.face_count > 1
        for face in result.faces:
            assert face.bounding_box.width > 0
            assert face.bounding_box.height > 0
