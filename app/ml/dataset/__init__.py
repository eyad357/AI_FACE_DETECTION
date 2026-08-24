"""
Dataset — labeled question -> intent examples for the ML intent
classifier.

Responsibility: load and validate the small, hand-curated CSV dataset
(intents.csv) used by app.ml.training to fit the TF-IDF + Logistic
Regression pipeline. This module does NOT train anything itself.

Dataset format (intents.csv):

    text,intent

    text:   a free-text student question (str, non-empty)
    intent: one of the IntentType names in app.models.schemas
            (INFORMATION, NAVIGATION, COMBINED, HELP). UNKNOWN is
            reserved for low-confidence runtime predictions and is
            intentionally NOT a labeled training class.

To extend the dataset: add more "text,intent" rows to intents.csv,
keeping the classes reasonably balanced, then re-run training (see
app.ml.training and docs/ml.md).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List

from app.models.schemas import IntentType

DATASET_DIR = Path(__file__).resolve().parent
DEFAULT_DATASET_PATH = DATASET_DIR / "intents.csv"

# Labeled training classes. UNKNOWN is a valid IntentType but is never a
# training label -- it only appears as a runtime fallback for
# low-confidence predictions (see app.ml.service).
_LABELED_INTENTS = frozenset(
    name for name in IntentType.__members__ if name != IntentType.UNKNOWN.name
)


class DatasetValidationError(ValueError):
    """Raised when the dataset file is missing, empty, or malformed."""


@dataclass(frozen=True)
class DatasetExample:
    """A single labeled training example."""

    text: str
    intent: str  # IntentType member name, e.g. "NAVIGATION"


def load_dataset(path: Path = DEFAULT_DATASET_PATH) -> List[DatasetExample]:
    """
    Load and validate the labeled dataset from a CSV file.

    Args:
        path: Path to a "text,intent" CSV file. Defaults to the bundled
            app/ml/dataset/intents.csv.

    Returns:
        A list of validated DatasetExample rows, in file order.

    Raises:
        DatasetValidationError: if the file is missing, empty, has the
            wrong header, contains an empty/blank text or an unknown
            intent label, or ends up empty after parsing.
    """
    if not path.exists():
        raise DatasetValidationError(f"Dataset file not found: {path}")

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != ["text", "intent"]:
            raise DatasetValidationError(
                "Dataset CSV must have header 'text,intent', got "
                f"{reader.fieldnames!r}"
            )

        examples: List[DatasetExample] = []
        for row_number, row in enumerate(reader, start=2):  # header is row 1
            text = (row.get("text") or "").strip()
            intent = (row.get("intent") or "").strip()

            if not text:
                raise DatasetValidationError(
                    f"Dataset row {row_number}: 'text' must not be empty"
                )
            if intent not in _LABELED_INTENTS:
                raise DatasetValidationError(
                    f"Dataset row {row_number}: unknown intent label "
                    f"{intent!r}. Expected one of {sorted(_LABELED_INTENTS)}"
                )
            examples.append(DatasetExample(text=text, intent=intent))

    if not examples:
        raise DatasetValidationError(f"Dataset file is empty: {path}")

    return examples


def dataset_class_counts(examples: List[DatasetExample]) -> dict:
    """Return a {intent_name: count} summary, useful for balance checks."""
    counts: dict = {}
    for example in examples:
        counts[example.intent] = counts.get(example.intent, 0) + 1
    return counts
