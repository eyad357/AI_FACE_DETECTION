"""
Reproducible training entry point for the shipped DEMO/fixture gesture
model.

Run with:

    python -m app.dl.training.train_fixture_model

This trains `GestureMLP` on the deterministic synthetic dataset from
`app.dl.dataset.fixture.generate_fixture_dataset` and saves the result
to `app.dl.config.DL_CONFIG.artifact_path` (by default
`app/dl/artifacts/gesture_mlp_fixture.npz`).

IMPORTANT — this is a demo/fixture pipeline run, not a claim of
real-world gesture-recognition accuracy. The dataset is synthetic
geometric patterns, not photographs of real hand gestures (see
docs/dl.md "Model lifecycle" and "Known limitations" in
PHASE_REPORT.md). To train on a REAL dataset instead, point
`load_dataset_from_directory` (see `app.dl.dataset.loader`) at a real
labeled image directory and swap it in below — no other DL code needs
to change (see docs/dl.md "Training command").
"""

from __future__ import annotations

from app.dl.config import DL_CONFIG
from app.dl.dataset.fixture import generate_fixture_dataset
from app.dl.models.network import GestureMLP
from app.dl.training.trainer import GestureTrainer
from app.utils.logger import get_logger

logger = get_logger(__name__)


def main() -> None:
    config = DL_CONFIG

    logger.info("Generating deterministic synthetic fixture dataset (seed=%d)", config.default_seed)
    X, y = generate_fixture_dataset(
        size=config.image_size,
        samples_per_class=40,
        noise_std=25.0,
        seed=config.default_seed,
    )

    logger.info(
        "Initializing GestureMLP (input_dim=%d, hidden=%d, classes=4, seed=%d)",
        config.input_dim,
        config.hidden_size,
        config.default_seed,
    )
    model = GestureMLP.from_seed(
        input_dim=config.input_dim,
        hidden_dim=config.hidden_size,
        num_classes=4,
        seed=config.default_seed,
    )

    trainer = GestureTrainer(learning_rate=0.5, epochs=200)
    result = trainer.train(model, X, y)

    print(
        f"Training complete on synthetic fixture dataset "
        f"({X.shape[0]} samples). Final training accuracy: "
        f"{result.final_train_accuracy:.4f} "
        f"(measured on the same synthetic distribution it was trained "
        f"on -- NOT a real-world gesture-recognition accuracy figure)."
    )

    result.model.save(config.artifact_path)
    print(f"Saved trained artifact to: {config.artifact_path}")


if __name__ == "__main__":
    main()
