"""
GestureMLP — the DL model itself.

A deliberately small, CPU-only, pure-NumPy two-layer perceptron
(Linear -> ReLU -> Linear -> Softmax). There is no PyTorch/TensorFlow
dependency: `requirements.txt` only provides `numpy`/`opencv-python`,
and a project this size does not justify adding a heavy framework
dependency just for a 4-class gesture classifier (see docs/dl.md
"Model implementation" for the full justification). The forward pass
is a few matrix multiplications; training (see
`app.dl.training.trainer`) is manual backpropagation — a legitimate,
non-trivial neural network, not a lookup table or a hardcoded label.

This module has no dependency on Vision, Robot, ML, Navigation,
Decision, Guide, or app.main. It depends only on NumPy.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

import numpy as np

from app.dl.models.gesture_types import DLError

_ARTIFACT_KEYS = ("W1", "b1", "W2", "b2")


def _softmax(logits: np.ndarray) -> np.ndarray:
    """Numerically stable softmax over the last axis."""
    shifted = logits - np.max(logits, axis=-1, keepdims=True)
    exp = np.exp(shifted)
    return exp / np.sum(exp, axis=-1, keepdims=True)


def _relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(0.0, x)


class GestureMLP:
    """
    A small feed-forward network: input -> hidden (ReLU) -> output
    (softmax over `num_classes`).

    Weights are plain NumPy float32 arrays. Construction is always
    explicit and deterministic given a seed (`from_seed`) or explicit
    weights (`__init__`) — there is no hidden global random state, so
    two `GestureMLP.from_seed(0, ...)` calls always produce bit-identical
    weights.
    """

    def __init__(
        self,
        W1: np.ndarray,
        b1: np.ndarray,
        W2: np.ndarray,
        b2: np.ndarray,
    ) -> None:
        for name, arr in (("W1", W1), ("b1", b1), ("W2", W2), ("b2", b2)):
            if not isinstance(arr, np.ndarray):
                raise DLError(f"GestureMLP.{name} must be a numpy array")
        if W1.ndim != 2 or W2.ndim != 2:
            raise DLError("GestureMLP.W1/W2 must be 2-D arrays")
        if b1.ndim != 1 or b2.ndim != 1:
            raise DLError("GestureMLP.b1/b2 must be 1-D arrays")
        input_dim, hidden_dim = W1.shape
        if b1.shape[0] != hidden_dim:
            raise DLError(
                f"GestureMLP.b1 shape {b1.shape} does not match hidden "
                f"dim {hidden_dim} implied by W1 shape {W1.shape}"
            )
        if W2.shape[0] != hidden_dim:
            raise DLError(
                f"GestureMLP.W2 shape {W2.shape} does not match hidden "
                f"dim {hidden_dim} implied by W1 shape {W1.shape}"
            )
        num_classes = W2.shape[1]
        if b2.shape[0] != num_classes:
            raise DLError(
                f"GestureMLP.b2 shape {b2.shape} does not match output "
                f"dim {num_classes} implied by W2 shape {W2.shape}"
            )

        self.W1 = W1.astype(np.float32, copy=True)
        self.b1 = b1.astype(np.float32, copy=True)
        self.W2 = W2.astype(np.float32, copy=True)
        self.b2 = b2.astype(np.float32, copy=True)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def from_seed(
        cls, input_dim: int, hidden_dim: int, num_classes: int, seed: int
    ) -> "GestureMLP":
        """
        Build a network with deterministic, seeded random weight
        initialization (standard scaled-normal / "He-ish" init).

        This is used both as the starting point for real training
        (`app.dl.training.trainer.GestureTrainer`) and, unmodified, as
        the explicitly-labeled "untrained fixture" fallback in
        `GestureRecognitionService` when no trained artifact is
        available (see docs/dl.md — such a network's predictions carry
        `metadata={"model_source": "untrained_fixture"}` and must never
        be interpreted as a real trained result).
        """
        if input_dim <= 0 or hidden_dim <= 0 or num_classes <= 0:
            raise DLError(
                "input_dim, hidden_dim, and num_classes must all be > 0, "
                f"got {input_dim}, {hidden_dim}, {num_classes}"
            )
        rng = np.random.default_rng(seed)
        W1 = rng.standard_normal((input_dim, hidden_dim)).astype(np.float32) * np.sqrt(
            2.0 / input_dim
        )
        b1 = np.zeros(hidden_dim, dtype=np.float32)
        W2 = rng.standard_normal((hidden_dim, num_classes)).astype(np.float32) * np.sqrt(
            2.0 / hidden_dim
        )
        b2 = np.zeros(num_classes, dtype=np.float32)
        return cls(W1, b1, W2, b2)

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def forward(self, x: np.ndarray) -> np.ndarray:
        """
        Run the forward pass.

        Args:
            x: shape (input_dim,) or (batch, input_dim), float.

        Returns:
            Class probabilities, shape (num_classes,) or
            (batch, num_classes), rows summing to ~1.0.
        """
        if not isinstance(x, np.ndarray):
            raise DLError(f"GestureMLP.forward expects a numpy array, got {type(x)!r}")
        single = x.ndim == 1
        batch = x[np.newaxis, :] if single else x
        if batch.ndim != 2 or batch.shape[1] != self.W1.shape[0]:
            raise DLError(
                f"GestureMLP.forward expects input of dim {self.W1.shape[0]}, "
                f"got shape {x.shape}"
            )
        hidden = _relu(batch.astype(np.float32) @ self.W1 + self.b1)
        logits = hidden @ self.W2 + self.b2
        probs = _softmax(logits)
        return probs[0] if single else probs

    @property
    def input_dim(self) -> int:
        return int(self.W1.shape[0])

    @property
    def hidden_dim(self) -> int:
        return int(self.W1.shape[1])

    @property
    def num_classes(self) -> int:
        return int(self.W2.shape[1])

    @property
    def num_params(self) -> int:
        return int(self.W1.size + self.b1.size + self.W2.size + self.b2.size)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Union[str, Path]) -> None:
        """Persist weights to a small `.npz` artifact."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(path, W1=self.W1, b1=self.b1, W2=self.W2, b2=self.b2)

    @classmethod
    def load(cls, path: Union[str, Path]) -> "GestureMLP":
        """
        Load weights from a `.npz` artifact produced by `save()`.

        Raises:
            DLError: if the file is missing, unreadable, or malformed
                (missing keys, wrong array shapes/ranks).
        """
        path = Path(path)
        if not path.exists():
            raise DLError(f"DL model artifact not found: {path}")
        try:
            with np.load(path) as data:
                missing = [k for k in _ARTIFACT_KEYS if k not in data]
                if missing:
                    raise DLError(
                        f"DL model artifact {path} is missing required "
                        f"array(s): {missing}"
                    )
                W1, b1, W2, b2 = (data[k] for k in _ARTIFACT_KEYS)
        except DLError:
            raise
        except Exception as exc:  # malformed/corrupt npz file
            raise DLError(f"Failed to load DL model artifact {path}: {exc}") from exc

        return cls(W1, b1, W2, b2)
