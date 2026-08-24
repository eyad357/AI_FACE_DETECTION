"""
Tests for app.dl.inference.preprocessing.

Require no GPU, camera, robot hardware, internet, or external services
-- all frames are synthetic NumPy arrays.
"""

import numpy as np
import pytest

from app.dl.models.gesture_types import DLError
from app.dl.inference.preprocessing import (
    preprocess_frame,
    resize_grayscale,
    to_grayscale,
)


class TestToGrayscale:
    def test_grayscale_passthrough(self):
        frame = np.full((10, 10), 128, dtype=np.uint8)
        gray = to_grayscale(frame)
        assert gray.shape == (10, 10)
        assert np.allclose(gray, 128.0)

    def test_bgr_conversion_shape(self):
        frame = np.zeros((8, 8, 3), dtype=np.uint8)
        frame[:, :, 2] = 255  # pure red in BGR order (B=0,G=0,R=255)
        gray = to_grayscale(frame)
        assert gray.shape == (8, 8)
        # Pure red should map to the R luma weight * 255.
        assert np.allclose(gray, 255 * 0.299)

    def test_bgra_uses_only_first_three_channels(self):
        frame = np.zeros((4, 4, 4), dtype=np.uint8)
        frame[:, :, 0] = 200  # B
        frame[:, :, 3] = 0  # alpha, should be ignored
        gray = to_grayscale(frame)
        assert np.allclose(gray, 200 * 0.114)


class TestResizeGrayscale:
    def test_output_shape_matches_requested_size(self):
        gray = np.arange(100, dtype=np.float32).reshape(10, 10)
        resized = resize_grayscale(gray, (5, 4))  # (width, height)
        assert resized.shape == (4, 5)

    def test_deterministic_repeated_calls(self):
        gray = np.random.default_rng(1).random((17, 23)).astype(np.float32)
        first = resize_grayscale(gray, (10, 10))
        second = resize_grayscale(gray, (10, 10))
        assert np.array_equal(first, second)

    def test_upsampling_does_not_crash(self):
        gray = np.ones((3, 3), dtype=np.float32) * 42
        resized = resize_grayscale(gray, (10, 10))
        assert resized.shape == (10, 10)
        assert np.allclose(resized, 42.0)


class TestPreprocessFrame:
    def test_valid_grayscale_frame(self):
        frame = np.full((40, 40), 255, dtype=np.uint8)
        features = preprocess_frame(frame, size=(20, 20))
        assert features.shape == (400,)
        assert features.dtype == np.float32
        assert np.all(features >= 0.0) and np.all(features <= 1.0)
        assert np.allclose(features, 1.0)

    def test_valid_color_frame(self):
        frame = np.zeros((40, 40, 3), dtype=np.uint8)
        features = preprocess_frame(frame, size=(20, 20))
        assert features.shape == (400,)
        assert np.allclose(features, 0.0)

    def test_deterministic_output(self):
        frame = np.random.default_rng(7).integers(0, 255, size=(30, 30, 3), dtype=np.uint8)
        first = preprocess_frame(frame, size=(20, 20))
        second = preprocess_frame(frame, size=(20, 20))
        assert np.array_equal(first, second)

    def test_none_frame_raises_dlerror(self):
        with pytest.raises(DLError):
            preprocess_frame(None, size=(20, 20))

    def test_non_ndarray_frame_raises_dlerror(self):
        with pytest.raises(DLError):
            preprocess_frame([[1, 2], [3, 4]], size=(20, 20))

    def test_wrong_ndim_raises_dlerror(self):
        frame = np.zeros((5, 5, 5, 5), dtype=np.uint8)
        with pytest.raises(DLError):
            preprocess_frame(frame, size=(20, 20))

    def test_unsupported_channel_count_raises_dlerror(self):
        frame = np.zeros((10, 10, 2), dtype=np.uint8)
        with pytest.raises(DLError):
            preprocess_frame(frame, size=(20, 20))

    def test_empty_frame_raises_dlerror(self):
        frame = np.zeros((0, 10, 3), dtype=np.uint8)
        with pytest.raises(DLError):
            preprocess_frame(frame, size=(20, 20))
