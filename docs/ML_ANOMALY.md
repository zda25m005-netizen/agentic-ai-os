# ML Anomaly Detection — Full Lifecycle (Phase C)

A real ML project living inside the OS: the mission runtime uses a trained,
served, monitored anomaly model as an "anomaly detected → evidence" step. Built
over Days 13-17 as a full lifecycle, not a decorative model.

| Day | Stage | Deliverable |
| --- | --- | --- |
| 13 | Dataset generation | synthetic transactions + labeled anomalies, splits, card |
| 14 | Feature engineering | leak-free feature pipeline (fit on train only) |
| 15 | Training + tracking | ≥3 models compared, logged to MLflow |
| 16 | Evaluation + registry | PR-AUC / precision / recall / F1, threshold, versioned artifact |
| 17 | Serving + monitoring | scorer + endpoint, drift/score panels, wired into a mission |

## Day 13 — Dataset generation

`ml/anomaly/data.py` generates a **reproducible** synthetic transaction stream.
Real fraud labels are scarce and private, so we synthesize a labeled stream we
fully control. Each user has a home country and a typical spend; normal
transactions are drawn around those, and a controlled fraction (`anomaly_rate`)
are replaced by one of five **labeled** anomaly patterns:

- **amount_spike** — 10-50x the user's normal amount
- **velocity** — a transaction seconds after the previous one
- **duplicate** — same amount + merchant as the prior transaction
- **off_hours** — activity forced into the 1-4am dead zone
- **geo_mismatch** — a country different from the user's home

Everything is seeded (`GeneratorConfig.seed`), so the same config yields
byte-identical data — that's what makes the downstream training and evaluation
reproducible.

### Splits + card

`split(rows)` produces a **stratified** train/val/test split (70/15/15 by
default), so the anomaly ratio is preserved in every split and no transaction
appears in two splits. `dataset_card(rows, cfg)` summarizes counts, actual vs
target anomaly rate, the per-type distribution, and the feature schema.

### Generating it

```bash
python -m ml.anomaly.make_dataset --n 5000 --seed 42 --out artifacts/anomaly
```

Writes `train/val/test.jsonl` + `card.json` + `card.md` under `artifacts/`
(gitignored — reproducible from the seed, so it's never committed).

### Tested

Reproducibility (same seed → identical), label balance within 2 points of target,
all five anomaly types present, label/type consistency, and stratified,
non-overlapping, deterministic splits.

## Day 14 — Feature engineering

`ml/anomaly/features.py` — a `FeaturePipeline` that learns its parameters **only
during `fit` on the training split** and applies them in `transform`, so a
val/test row's features never depend on other rows in its split (**no train/test
leakage**). Unseen users/categories fall back to global defaults.

Learned on train: per-user spend mean/std, each user's home country, category and
country frequencies, and global amount stats. Each transaction maps to a
**fixed-length 14-d vector**:

- **temporal** — cyclical hour (`sin`/`cos`), off-hours flag, weekday, weekend
- **amount** — `log_amount`, ratio to the user's mean, z-score vs user and vs
  population
- **velocity** — `log(seconds_since_prev)`, rapid-fire flag (< 60s)
- **geo** — is-home-country
- **encodings** — frequency encoding for country and category

`to_xy(pipeline, rows)` returns the `(X, y)` matrix/labels a model trains on.

### Tested

Fixed 14-d schema, `fit_transform` determinism, transform-before-fit guard,
**leakage check** (a row transforms identically in isolation vs within its split),
train-only fit (learned params unchanged by val data), unseen-user global
fallback, and that the off-hours / rapid flags actually fire on injected anomalies.

## Day 15 — Training + experiment tracking

`ml/anomaly/train.py` fits the feature pipeline on train, standardizes, trains
every available model, scores the validation split, and logs ROC-AUC + PR-AUC per
run. Three models are implemented in **pure numpy** so they always run (CI too):

- **GaussianScorer** — unsupervised per-feature Gaussian; summed z-distance.
- **LogisticRegressionNP** — supervised, class-weighted for imbalance.
- **AutoencoderNP** — small MLP autoencoder on normal rows; reconstruction error.

Two more — **IsolationForest** and **GradientBoosting** — are added automatically
when scikit-learn is installed, so a local run compares **five** models and CI
compares **three**.

**Experiment tracking** (`tracking.py`) uses **MLflow** when installed, else a
local JSON store under `artifacts/anomaly/runs/` — params/metrics logged either
way, so runs stay reproducible in CI without the heavy dependency.

### Real numbers (seed 42, n=4000, numpy models)

| model | ROC-AUC | PR-AUC |
| --- | --- | --- |
| logreg | 0.980 | 0.884 |
| gaussian | 0.961 | 0.881 |
| autoencoder | 0.938 | 0.879 |

These are actual outputs of `python -m ml.anomaly.train`, reproducible from the
seed — not illustrative placeholders. (Install `scikit-learn mlflow` to add the
two tree models and MLflow tracking.)

### Tested

Metric correctness (ROC-AUC extremes, average precision, F1, single-class guard),
each model separating anomalies above an AUC floor on held-out data, ≥3 models
available, and the training loop ranking models by PR-AUC and logging every run.

## Day 16 — Evaluation + model registry

`ml/anomaly/evaluate.py` reports metrics **honestly**: models train on **train**,
the operating **threshold is chosen on validation** (best-F1), and every reported
number — ROC-AUC, PR-AUC, precision/recall/F1, Brier calibration — is computed on
the held-out **test** split. The winner is selected by validation PR-AUC (no test
peeking) and reported on test.

- `best_f1_threshold` / `threshold_at_recall` — pick an operating point.
- `brier_score` — calibration for probabilistic models (returns `None` for
  score-based models whose outputs aren't probabilities).
- `evaluate_all` — the full table + winner.

`ml/anomaly/registry.py` is a tiny **versioned registry**: `save_model` writes a
new `vN/` directory with the pickled artifact (model + feature pipeline +
standardizer + threshold), `metrics.json`, and `meta.json`; versions
auto-increment and `load_model` reloads any version for serving. The evaluate CLI
promotes the winner automatically:

```bash
python -m ml.anomaly.evaluate --n 5000 --seed 42
```

The full run (with scikit-learn installed) compares five models on test, chooses
the winner by validation PR-AUC, and saves it as `v1`. Because the threshold is
transferred from validation, some models trade recall for precision on test —
that honest behavior is exactly what the report surfaces.

### Tested

Threshold selection on separable data (F1 = 1.0), `threshold_at_recall` meeting
its target, Brier extremes + the non-probability guard, the end-to-end evaluation
producing a test-set table ranked by PR-AUC with a winner, and a registry
save/load roundtrip with auto-incrementing versions.

## Day 17 — Serving + monitoring + mission integration (Phase C milestone)

The trained model now lives in the running system, not just a notebook.

- **Serving** (`serving.py`) — `Scorer.from_registry()` loads the promoted
  artifact (model + feature pipeline + standardizer + threshold) and scores a raw
  transaction dict end to end (missing temporal fields are derived from the
  timestamp). `anomaly_evidence()` turns a score into a mission-ready evidence
  record.
- **Monitoring** (`monitoring.py`) — `psi` (Population Stability Index) and
  `ks_statistic` detect input/score **drift** vs a training-time reference;
  `ScoreMonitor` reports drift + distribution summaries. Pure numpy.
- **Metrics** — `app/obs/metrics.py` adds `agentic_anomaly_scored_total`,
  `agentic_anomaly_flagged_total`, an `agentic_anomaly_score` histogram, and an
  `agentic_anomaly_drift_psi` gauge, all scraped at `/metrics` for Grafana.
- **API** (`app/api/anomaly.py`) — `GET /anomaly/status`, `POST /anomaly/score`
  (records metrics; 503 if no model is promoted), `POST /anomaly/drift`
  (PSI/KS + publishes the gauge).
- **Mission integration** — `anomaly_scan` is a registered agent tool: a mission
  can score a transaction and get back structured evidence (is_anomaly, score,
  threshold, model version) to reason over — the "anomaly detected → evidence"
  step. It degrades gracefully when no model is in the registry.

**Milestone reached:** a real, served, monitored ML model driving agent decisions.

### Tested

`transaction_from_dict` field derivation, a scorer flagging a large amount over a
normal one, evidence shape, PSI≈0 for identical distributions and >0.25 under a
shift, KS extremes, `ScoreMonitor` drift flagging, the `/anomaly` endpoints
(status/score/drift + 503 fallback), and that `anomaly_scan` is registered.
