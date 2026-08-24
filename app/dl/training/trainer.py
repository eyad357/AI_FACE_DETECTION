"""
GestureTrainer — trains a `GestureMLP` with real gradient descent.

This is manual forward/backward-pass backpropagation (cross-entropy
loss over a softmax output, ReLU hidden layer) implemented directly in
NumPy — deliberately not a black box and not a fake. No autodiff
framework is used or needed for a network this small; the full
gradient derivation is the handful of matrix operations below.

Determinism: given the same `seed`, the same initial weights (from
`GestureMLP.from_seed`), and the same `(X, y)`, training always
produces bit-identical resulting weights — no shuffling, dropout, or
other hidden randomness occurs inside `GestureTrainer` itself (any
shuffling belongs to dataset generation, e.g.
`app.dl.dataset.fixture.generate_fixture_dataset`, which is itself
seeded).

This module has no dependency on Vision, Robot, ML, Navigation,
Decision, Guide, or app.main.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np

from app.dl.models.gesture_types import DLError
from app.dl.models.network import GestureMLP
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class TrainingResult:
    """Outcome of a `GestureTrainer.train()` call."""

    model: GestureMLP
    loss_history: List[float]
    final_train_accuracy: float


def _one_hot(y: np.ndarray, num_classes: int) -> np.ndarray:
    out = np.zeros((y.shape[0], num_classes), dtype=np.float32)
    out[np.arange(y.shape[0]), y] = 1.0
    return out


class GestureTrainer:
    """Trains a `GestureMLP` via full-batch gradient descent."""

    def __init__(self, learning_rate: float = 0.5, epochs: int = 200) -> None:
        if learning_rate <= 0:
            raise DLError(f"learning_rate must be > 0, got {learning_rate}")
        if epochs <= 0:
            raise DLError(f"epochs must be > 0, got {epochs}")
        self.learning_rate = learning_rate
        self.epochs = epochs

    def train(self, model: GestureMLP, X: np.ndarray, y: np.ndarray) -> TrainingResult:
        """
        Train `model` in place-equivalent fashion (returns a new
        `GestureMLP` with updated weights; does not mutate the input
        model's arrays).

        Args:
            model: A `GestureMLP` to start from (e.g.
                `GestureMLP.from_seed(...)`).
            X: shape (N, input_dim), float32, in [0, 1].
            y: shape (N,), int64 class indices in
                [0, model.num_classes).

        Returns:
            A `TrainingResult` with the trained model, per-epoch loss
            history, and final training-set accuracy.

        Raises:
            DLError: if `X`/`y` shapes are inconsistent with each
                other or with `model`.
        """
        if X.ndim != 2 or X.shape[1] != model.input_dim:
            raise DLError(
                f"X must have shape (N, {model.input_dim}), got {X.shape}"
            )
        if y.ndim != 1 or y.shape[0] != X.shape[0]:
            raise DLError(
                f"y must have shape ({X.shape[0]},), got {y.shape}"
            )
        if y.min() < 0 or y.max() >= model.num_classes:
            raise DLError(
                f"y contains labels outside [0, {model.num_classes}), "
                f"got range [{y.min()}, {y.max()}]"
            )

        W1, b1, W2, b2 = (
            model.W1.copy(),
            model.b1.copy(),
            model.W2.copy(),
            model.b2.copy(),
        )
        Y = _one_hot(y, model.num_classes)
        n = X.shape[0]
        loss_history: List[float] = []

        for epoch in range(self.epochs):
            # Forward pass.
            z1 = X @ W1 + b1
            h1 = np.maximum(0.0, z1)
            logits = h1 @ W2 + b2
            shifted = logits - np.max(logits, axis=1, keepdims=True)
            exp = np.exp(shifted)
            probs = exp / np.sum(exp, axis=1, keepdims=True)

            # Cross-entropy loss (mean over the batch), with a small
            # epsilon to avoid log(0).
            eps = 1e-9
            loss = float(-np.mean(np.sum(Y * np.log(probs + eps), axis=1)))
            loss_history.append(loss)

            # Backward pass (manual gradients).
            d_logits = (probs - Y) / n  # dL/d(logits)
            d_W2 = h1.T @ d_logits
            d_b2 = np.sum(d_logits, axis=0)
            d_h1 = d_logits @ W2.T
            d_z1 = d_h1 * (z1 > 0)  # ReLU gradient
            d_W1 = X.T @ d_z1
            d_b1 = np.sum(d_z1, axis=0)

            # SGD update.
            W1 -= self.learning_rate * d_W1
            b1 -= self.learning_rate * d_b1
            W2 -= self.learning_rate * d_W2
            b2 -= self.learning_rate * d_b2

            if epoch == 0 or (epoch + 1) % max(1, self.epochs // 5) == 0:
                logger.debug("Epoch %d/%d loss=%.4f", epoch + 1, self.epochs, loss)

        trained_model = GestureMLP(W1, b1, W2, b2)
        final_preds = np.argmax(trained_model.forward(X), axis=1)
        final_accuracy = float(np.mean(final_preds == y))

        return TrainingResult(
            model=trained_model,
            loss_history=loss_history,
            final_train_accuracy=final_accuracy,
        )
