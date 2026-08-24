"""
Tests for app.dl.models.network.GestureMLP.

Require no GPU, camera, robot hardware, internet, or external services.
"""

import numpy as np
import pytest

from app.dl.models.gesture_types import DLError
from app.dl.models.network import GestureMLP


class TestConstruction:
    def test_valid_construction(self):
        rng = np.random.default_rng(0)
        model = GestureMLP(
            W1=rng.standard_normal((10, 5)).astype(np.float32),
            b1=np.zeros(5, dtype=np.float32),
            W2=rng.standard_normal((5, 4)).astype(np.float32),
            b2=np.zeros(4, dtype=np.float32),
        )
        assert model.input_dim == 10
        assert model.hidden_dim == 5
        assert model.num_classes == 4

    def test_mismatched_shapes_raise_dlerror(self):
        with pytest.raises(DLError):
            GestureMLP(
                W1=np.zeros((10, 5), dtype=np.float32),
                b1=np.zeros(4, dtype=np.float32),  # wrong length
                W2=np.zeros((5, 4), dtype=np.float32),
                b2=np.zeros(4, dtype=np.float32),
            )

    def test_non_array_weights_raise_dlerror(self):
        with pytest.raises(DLError):
            GestureMLP(W1=[[1, 2]], b1=np.zeros(2), W2=np.zeros((2, 4)), b2=np.zeros(4))


class TestFromSeed:
    def test_deterministic_given_same_seed(self):
        m1 = GestureMLP.from_seed(input_dim=20, hidden_dim=6, num_classes=4, seed=42)
        m2 = GestureMLP.from_seed(input_dim=20, hidden_dim=6, num_classes=4, seed=42)
        assert np.array_equal(m1.W1, m2.W1)
        assert np.array_equal(m1.b1, m2.b1)
        assert np.array_equal(m1.W2, m2.W2)
        assert np.array_equal(m1.b2, m2.b2)

    def test_different_seeds_produce_different_weights(self):
        m1 = GestureMLP.from_seed(input_dim=20, hidden_dim=6, num_classes=4, seed=1)
        m2 = GestureMLP.from_seed(input_dim=20, hidden_dim=6, num_classes=4, seed=2)
        assert not np.array_equal(m1.W1, m2.W1)

    def test_invalid_dims_raise_dlerror(self):
        with pytest.raises(DLError):
            GestureMLP.from_seed(input_dim=0, hidden_dim=6, num_classes=4, seed=0)
        with pytest.raises(DLError):
            GestureMLP.from_seed(input_dim=20, hidden_dim=-1, num_classes=4, seed=0)


class TestForward:
    def test_single_sample_shape_and_softmax_sums_to_one(self):
        model = GestureMLP.from_seed(input_dim=12, hidden_dim=6, num_classes=4, seed=0)
        x = np.random.default_rng(0).random(12).astype(np.float32)
        probs = model.forward(x)
        assert probs.shape == (4,)
        assert np.isclose(probs.sum(), 1.0, atol=1e-5)
        assert np.all(probs >= 0.0)

    def test_batch_shape_and_softmax_sums_to_one(self):
        model = GestureMLP.from_seed(input_dim=12, hidden_dim=6, num_classes=4, seed=0)
        x = np.random.default_rng(0).random((5, 12)).astype(np.float32)
        probs = model.forward(x)
        assert probs.shape == (5, 4)
        assert np.allclose(probs.sum(axis=1), 1.0, atol=1e-5)

    def test_deterministic_forward_pass(self):
        model = GestureMLP.from_seed(input_dim=12, hidden_dim=6, num_classes=4, seed=0)
        x = np.ones(12, dtype=np.float32)
        first = model.forward(x)
        second = model.forward(x)
        assert np.array_equal(first, second)

    def test_non_array_input_raises_dlerror(self):
        model = GestureMLP.from_seed(input_dim=12, hidden_dim=6, num_classes=4, seed=0)
        with pytest.raises(DLError):
            model.forward([1.0] * 12)

    def test_wrong_input_dim_raises_dlerror(self):
        model = GestureMLP.from_seed(input_dim=12, hidden_dim=6, num_classes=4, seed=0)
        with pytest.raises(DLError):
            model.forward(np.ones(5, dtype=np.float32))


class TestSaveLoadRoundTrip:
    def test_round_trip_preserves_weights_exactly(self, tmp_path):
        model = GestureMLP.from_seed(input_dim=16, hidden_dim=8, num_classes=4, seed=3)
        path = tmp_path / "model.npz"
        model.save(path)
        loaded = GestureMLP.load(path)
        assert np.array_equal(model.W1, loaded.W1)
        assert np.array_equal(model.b1, loaded.b1)
        assert np.array_equal(model.W2, loaded.W2)
        assert np.array_equal(model.b2, loaded.b2)

    def test_round_trip_preserves_predictions(self, tmp_path):
        model = GestureMLP.from_seed(input_dim=16, hidden_dim=8, num_classes=4, seed=3)
        path = tmp_path / "model.npz"
        model.save(path)
        loaded = GestureMLP.load(path)
        x = np.random.default_rng(0).random(16).astype(np.float32)
        assert np.allclose(model.forward(x), loaded.forward(x))

    def test_load_missing_file_raises_dlerror(self, tmp_path):
        with pytest.raises(DLError):
            GestureMLP.load(tmp_path / "does_not_exist.npz")

    def test_load_malformed_artifact_raises_dlerror(self, tmp_path):
        path = tmp_path / "malformed.npz"
        np.savez(path, W1=np.zeros((4, 4)))  # missing b1/W2/b2
        with pytest.raises(DLError):
            GestureMLP.load(path)

    def test_load_corrupt_file_raises_dlerror(self, tmp_path):
        path = tmp_path / "corrupt.npz"
        path.write_bytes(b"not a real npz file")
        with pytest.raises(DLError):
            GestureMLP.load(path)
