# ML — Intent Classification

Owner: Person 1 (AI / Intelligence).

## 1. Purpose

Given a student's free-text question, determine what they are asking
for — an *intent* — so a future orchestration layer can decide how to
respond.

## 2. Responsibility

ML answers exactly one question: **"What is the student asking for?"**

ML does **not**:

- decide what to do about the intent (route to Guide, Navigation, or a
  help response)
- speak, move the robot, or render anything
- know about Vision, Decision, Guide, Navigation, Robot, DL, or UI

That orchestration is a future phase's job, mirroring how `app.decision`
owns state and `app.guide` owns content today, without either one
directly driving the robot.

## 3. Architecture

```
Student Question (str)
      |
      v
MLIntentService.predict()   (app.ml.service)
      |
      v
IntentResult                (app.models.schemas)
```

Internally, `MLIntentService` delegates to:

```
app.ml.service
      |
      v
app.ml.inference.inference   (loads trained artifact, runs prediction)
      |
      v
app.ml.artifacts/intent_classifier.joblib   (trained offline)
```

Offline, separately, training is:

```
app.ml.dataset (intents.csv)
      |
      v
app.ml.training.train   (TF-IDF + Logistic Regression, evaluation)
      |
      v
app.ml.artifacts/intent_classifier.joblib
```

Training and inference are deliberately split: **training never runs at
request time**, and **inference never retrains**.

### Package layout

```
app/ml/
├── __init__.py         module overview
├── dataset/
│   ├── __init__.py     load_dataset() + validation
│   └── intents.csv     labeled "text,intent" examples
├── training/
│   ├── __init__.py
│   └── train.py         offline training pipeline (run manually)
├── inference/
│   ├── __init__.py
│   └── inference.py     runtime prediction from a trained artifact
├── artifacts/
│   ├── README.md
│   └── intent_classifier.joblib   trained pipeline (committed)
└── service.py            public API: MLIntentService
```

## 4. Intent classes

| Intent | Meaning | Example |
|---|---|---|
| `INFORMATION` | Wants to know *about* something | "Tell me about the AI Lab." |
| `NAVIGATION` | Wants to get *to* somewhere | "Where is the AI Lab?" |
| `COMBINED` | Wants both directions and information | "Where is the AI Lab and what can I do there?" |
| `HELP` | Doesn't know what to ask / needs assistance | "I need help." |
| `UNKNOWN` | Runtime-only fallback; never a training label (see below) | — |

`IntentType` and `IntentResult` live in `app.models.schemas` — the
project's single canonical contracts module — not in `app.ml`, so any
future consumer can depend on the contract without depending on ML's
implementation.

`UNKNOWN` is returned at runtime (not trained on) when the input is
empty/blank, or when the model's confidence falls below
`CONFIG.ml.min_confidence` (0.0 by default — effectively disabled unless
explicitly configured).

## 5. Dataset format

`app/ml/dataset/intents.csv`:

```csv
text,intent
Where is the AI Lab?,NAVIGATION
Tell me about the AI Lab.,INFORMATION
```

- `text`: free-text student question (non-empty).
- `intent`: one of `INFORMATION`, `NAVIGATION`, `COMBINED`, `HELP`
  (must match an `IntentType` member name; `UNKNOWN` is rejected as a
  training label — see `DatasetValidationError`).

The bundled dataset has 59 hand-written, realistic examples, kept
reasonably balanced (12–18 per class) rather than mechanically
duplicated.

## 6. Training process

Offline only, using `scikit-learn`:

1. Load and validate `intents.csv` (`app.ml.dataset.load_dataset`).
2. Stratified train/test split (75/25, fixed random seed for
   reproducibility).
3. Fit a `TfidfVectorizer` (unigrams + bigrams) on the training texts.
4. Fit a `LogisticRegression` classifier on the TF-IDF vectors.
5. Evaluate on the held-out test split (accuracy + per-class
   precision/recall/F1).
6. Persist the fitted `sklearn.pipeline.Pipeline` (vectorizer + classifier
   together) to `app/ml/artifacts/intent_classifier.joblib` via `joblib`.

Training **never** happens automatically as a side effect of importing
`app.ml` or running the application — it is a separate, explicit step
(see "How to train" below).

## 7. Runtime inference

1. `MLIntentService.predict(text)` is called with raw text.
2. Empty/blank/non-string input short-circuits to `IntentResult(UNKNOWN,
   confidence=0.0, raw_text=...)` without touching the model at all.
3. Otherwise, `app.ml.inference.inference.predict_intent` loads the
   trained pipeline (cached in-process after the first load) and calls
   `pipeline.predict_proba([text])`.
4. The highest-probability class and its probability become the
   predicted intent and confidence.
5. If confidence is below `CONFIG.ml.min_confidence`, the intent is
   downgraded to `UNKNOWN` (confidence is still reported as the model's
   actual value, not zeroed).
6. The result is wrapped in a validated `IntentResult`.

If no trained artifact exists on disk, `predict_intent` raises
`ArtifactNotFoundError` immediately — it does **not** silently trigger
training.

## 8. TF-IDF explanation

TF-IDF (Term Frequency–Inverse Document Frequency) turns each question
into a numeric vector where each dimension is a word (or word pair, via
bigrams) and its value reflects how distinctive that term is for the
question — common words like "the" contribute little, while
topic-specific words like "library" or "help" contribute more. This
requires no external model download and is fast and fully explainable.

## 9. Logistic Regression explanation

Logistic Regression is a simple linear classifier: given the TF-IDF
vector, it learns a weight for each term/class pair and picks the class
whose weighted sum is highest, converting that into a probability via
the softmax/logistic function. It is lightweight, deterministic given a
fixed seed, and easy to inspect — a good match for a small,
explainable, university robotics project (as opposed to a neural
network or LLM, which are explicitly out of scope for this phase).

## 10. `IntentResult` contract

Defined in `app/models/schemas.py` (the project's single canonical
contracts module):

```python
class IntentType(Enum):
    INFORMATION = "INFORMATION"
    NAVIGATION = "NAVIGATION"
    COMBINED = "COMBINED"
    HELP = "HELP"
    UNKNOWN = "UNKNOWN"

@dataclass(frozen=True)
class IntentResult:
    intent: IntentType
    confidence: float   # validated to be within [0.0, 1.0]
    raw_text: str
```

## 11. How to train

```bash
cd ai-university-lab-guide
pip install -r requirements.txt
python -m app.ml.training.train
```

Optional flags:

```bash
python -m app.ml.training.train --dataset path/to/other.csv --out path/to/artifact.joblib
```

This prints train/test sizes, accuracy, a per-class report, and the
artifact path, then writes the trained pipeline to
`app/ml/artifacts/intent_classifier.joblib` (or `--out`).

## 12. How to run inference

```python
from app.ml.service import MLIntentService

service = MLIntentService()
result = service.predict("Where is the AI Lab?")
print(result.intent, result.confidence)
```

## 13. How to run tests

```bash
# ML tests only
pytest tests/ml/ -v

# Full suite (existing + ML)
pytest -v
```

## 14. Evaluation metrics

On the bundled 59-example dataset (44 train / 15 test, fixed seed),
the committed artifact achieves **~0.73 accuracy** on the held-out
split, with per-class precision/recall printed by the training script.
This is expected to be modest given the deliberately small, non-repetitive
dataset (see Section 22 of the phase spec: "do not generate hundreds of
nearly identical examples just to increase dataset size"). Accuracy
improves as the dataset (Section 15, "How to extend the dataset") grows
with more realistic phrasing.

## 15. How to extend the dataset

1. Add new rows to `app/ml/dataset/intents.csv` in the format
   `text,intent`.
2. Keep classes reasonably balanced — avoid dumping dozens of near-
   duplicate phrasings into one class.
3. Re-run training: `python -m app.ml.training.train`.
4. Re-run `pytest tests/ml/` to confirm nothing broke.
5. Commit the updated `intents.csv` and the regenerated
   `intent_classifier.joblib` together.

## 16. How to add a future intent safely

1. Add the new member to `IntentType` in `app/models/schemas.py` (the
   single canonical contracts module — do not create a duplicate enum
   in `app.ml`).
2. Add labeled examples for the new intent to `intents.csv`.
3. Re-train (`python -m app.ml.training.train`) and re-run
   `tests/ml/test_dataset.py::TestLoadDefaultDataset::test_all_intents_represented`
   to confirm the loader picks it up automatically (it derives its
   expected set from `IntentType` rather than a hard-coded list).
4. Add classification test cases for the new intent to
   `tests/ml/test_service.py`.
5. Update this document's intent table (Section 4).

## ML does not perform integration

This phase adds `app.ml` as a self-contained module that is **ready**
for future integration. It does not modify `app.main`, and it does not
call `Decision`, `Guide`, `Navigation`, `Robot`, `Vision`, `DL`, or
`UI`. Wiring `IntentResult` into the orchestration layer is explicitly
out of scope and belongs to a later phase.
