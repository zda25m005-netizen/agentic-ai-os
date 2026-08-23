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
