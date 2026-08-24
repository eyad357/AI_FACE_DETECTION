"""
Tests for app.dl.dataset.fixture and app.dl.training.trainer.

Require no GPU, camera, robot hardware, internet, or external services
-- the dataset is entirely synthetic and generated in-process.
"""

import numpy as np
import pytest

from app.dl.dataset.fixture import FIXTURE_LABEL_ORDER, generate_fixture_dataset
from app.dl.models.gesture_types import DLError
from app.dl.models.network import GestureMLP
from app.dl.training.trainer import GestureTrainer


class TestGenerateFixtureDataset:
    def test_shapes(self):
        X, y = generate_fixture_dataset(size=(10, 10), samples_per_class=5, seed=0)
        assert X.shape == (20, 100)
        assert y.shape == (20,)
        assert X.dtype == np.float32
        assert set(np.unique(y)) == {0, 1, 2, 3}

    def test_values_in_unit_range(self):
        X, _ = generate_fixture_dataset(size=(10, 10), samples_per_class=5, seed=0)
        assert np.all(X >= 0.0) and np.all(X <= 1.0)

    def test_deterministic_given_same_seed(self):
        X1, y1 = generate_fixture_dataset(size=(10, 10), samples_per_class=5, seed=99)
        X2, y2 = generate_fixture_dataset(size=(10, 10), samples_per_class=5, seed=99)
        assert np.array_equal(X1, X2)
        assert np.array_equal(y1, y2)

    def test_different_seeds_produce_different_data(self):
        X1, _ = generate_fixture_dataset(size=(10, 10), samples_per_class=5, seed=1)
        X2, _ = generate_fixture_dataset(size=(10, 10), samples_per_class=5, seed=2)
        assert not np.array_equal(X1, X2)

    def test_invalid_samples_per_class_raises(self):
        with pytest.raises(ValueError):
            generate_fixture_dataset(size=(10, 10), samples_per_class=0, seed=0)

    def test_label_order_matches_gesture_vocabulary(self):
        values = {label.value for label in FIXTURE_LABEL_ORDER}
        assert values == {"WAVE", "STOP", "POINT", "UNKNOWN"}


class TestGestureTrainer:
    def test_training_reduces_loss(self):
        X, y = generate_fixture_dataset(size=(10, 10), samples_per_class=10, seed=0)
        model = GestureMLP.from_seed(input_dim=100, hidden_dim=12, num_classes=4, seed=0)
        trainer = GestureTrainer(learning_rate=0.5, epochs=100)
        result = trainer.train(model, X, y)
        assert result.loss_history[-1] < result.loss_history[0]

    def test_training_learns_the_fixture_task_well(self):
        X, y = generate_fixture_dataset(size=(10, 10), samples_per_class=10, seed=0)
        model = GestureMLP.from_seed(input_dim=100, hidden_dim=12, num_classes=4, seed=0)
        trainer = GestureTrainer(learning_rate=0.5, epochs=150)
        result = trainer.train(model, X, y)
        # A small, cleanly-separable synthetic task should be learnable
        # to high accuracy; this is a sanity check on the pipeline, not
        # a real-world accuracy claim (see docs/dl.md).
        assert result.final_train_accuracy > 0.9

    def test_training_deterministic_given_same_seed(self):
        X, y = generate_fixture_dataset(size=(10, 10), samples_per_class=10, seed=0)
        model1 = GestureMLP.from_seed(input_dim=100, hidden_dim=12, num_classes=4, seed=5)
        model2 = GestureMLP.from_seed(input_dim=100, hidden_dim=12, num_classes=4, seed=5)
        trainer = GestureTrainer(learning_rate=0.5, epochs=30)
        result1 = trainer.train(model1, X, y)
        result2 = trainer.train(model2, X, y)
        assert np.array_equal(result1.model.W1, result2.model.W1)
        assert np.array_equal(result1.model.W2, result2.model.W2)
        assert result1.loss_history == result2.loss_history

    def test_trained_model_does_not_mutate_input_model(self):
        X, y = generate_fixture_dataset(size=(10, 10), samples_per_class=10, seed=0)
        model = GestureMLP.from_seed(input_dim=100, hidden_dim=12, num_classes=4, seed=0)
        original_W1 = model.W1.copy()
        trainer = GestureTrainer(learning_rate=0.5, epochs=10)
        trainer.train(model, X, y)
        assert np.array_equal(model.W1, original_W1)

    def test_mismatched_input_dim_raises_dlerror(self):
        X, y = generate_fixture_dataset(size=(10, 10), samples_per_class=5, seed=0)
        model = GestureMLP.from_seed(input_dim=50, hidden_dim=6, num_classes=4, seed=0)
        trainer = GestureTrainer(learning_rate=0.1, epochs=5)
        with pytest.raises(DLError):
            trainer.train(model, X, y)

    def test_out_of_range_labels_raise_dlerror(self):
        X, _ = generate_fixture_dataset(size=(10, 10), samples_per_class=5, seed=0)
        bad_y = np.zeros(X.shape[0], dtype=np.int64)
        bad_y[0] = 99
        model = GestureMLP.from_seed(input_dim=100, hidden_dim=6, num_classes=4, seed=0)
        trainer = GestureTrainer(learning_rate=0.1, epochs=5)
        with pytest.raises(DLError):
            trainer.train(model, X, bad_y)

    def test_invalid_hyperparameters_raise_dlerror(self):
        with pytest.raises(DLError):
            GestureTrainer(learning_rate=0.0, epochs=10)
        with pytest.raises(DLError):
            GestureTrainer(learning_rate=0.1, epochs=0)
