"""Tests for app.models.schemas — the canonical shared data contracts."""

from datetime import datetime, timezone

import pytest

from app.models.schemas import BoundingBox, DetectionResult, FaceDetection


class TestBoundingBox:
    def test_valid_bounding_box(self):
        box = BoundingBox(x=10, y=20, width=100, height=120)
        assert box.x == 10
        assert box.area == 100 * 120

    def test_negative_coordinates_rejected(self):
        with pytest.raises(ValueError):
            BoundingBox(x=-1, y=0, width=10, height=10)

    def test_non_positive_dimensions_rejected(self):
        with pytest.raises(ValueError):
            BoundingBox(x=0, y=0, width=0, height=10)
        with pytest.raises(ValueError):
            BoundingBox(x=0, y=0, width=10, height=-5)

    def test_center(self):
        box = BoundingBox(x=0, y=0, width=10, height=20)
        assert box.center == (5.0, 10.0)


class TestFaceDetection:
    def test_valid_without_confidence(self):
        face = FaceDetection(bounding_box=BoundingBox(0, 0, 10, 10))
        assert face.confidence is None

    def test_valid_with_confidence(self):
        face = FaceDetection(
            bounding_box=BoundingBox(0, 0, 10, 10), confidence=0.87
        )
        assert face.confidence == 0.87

    def test_confidence_out_of_range_rejected(self):
        with pytest.raises(ValueError):
            FaceDetection(bounding_box=BoundingBox(0, 0, 10, 10), confidence=1.5)
        with pytest.raises(ValueError):
            FaceDetection(bounding_box=BoundingBox(0, 0, 10, 10), confidence=-0.1)


class TestDetectionResult:
    def test_empty_factory(self):
        result = DetectionResult.empty()
        assert result.detected is False
        assert result.face_count == 0
        assert result.faces == []
        assert result.confidence is None

    def test_valid_single_face(self):
        face = FaceDetection(bounding_box=BoundingBox(0, 0, 10, 10))
        result = DetectionResult(
            detected=True,
            face_count=1,
            confidence=None,
            timestamp=datetime.now(timezone.utc),
            faces=[face],
        )
        assert result.face_count == 1
        assert len(result.faces) == 1

    def test_valid_multiple_faces(self):
        faces = [
            FaceDetection(bounding_box=BoundingBox(0, 0, 10, 10)),
            FaceDetection(bounding_box=BoundingBox(20, 20, 10, 10)),
        ]
        result = DetectionResult(
            detected=True,
            face_count=2,
            confidence=None,
            timestamp=datetime.now(timezone.utc),
            faces=faces,
        )
        assert result.face_count == 2

    def test_detected_true_requires_faces(self):
        with pytest.raises(ValueError):
            DetectionResult(
                detected=True,
                face_count=0,
                confidence=None,
                timestamp=datetime.now(timezone.utc),
                faces=[],
            )

    def test_detected_false_requires_zero_count(self):
        with pytest.raises(ValueError):
            DetectionResult(
                detected=False,
                face_count=1,
                confidence=None,
                timestamp=datetime.now(timezone.utc),
                faces=[FaceDetection(bounding_box=BoundingBox(0, 0, 10, 10))],
            )

    def test_face_count_mismatch_rejected(self):
        with pytest.raises(ValueError):
            DetectionResult(
                detected=True,
                face_count=2,
                confidence=None,
                timestamp=datetime.now(timezone.utc),
                faces=[FaceDetection(bounding_box=BoundingBox(0, 0, 10, 10))],
            )

    def test_negative_face_count_rejected(self):
        with pytest.raises(ValueError):
            DetectionResult(
                detected=False,
                face_count=-1,
                confidence=None,
                timestamp=datetime.now(timezone.utc),
                faces=[],
            )

    def test_confidence_out_of_range_rejected(self):
        with pytest.raises(ValueError):
            DetectionResult(
                detected=False,
                face_count=0,
                confidence=1.2,
                timestamp=datetime.now(timezone.utc),
                faces=[],
            )
