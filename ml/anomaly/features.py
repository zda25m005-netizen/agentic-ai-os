"""Feature engineering for anomaly detection — leak-free, fit on train only.

The pipeline learns its parameters (per-user spend aggregates, the user's home
country, category/country frequencies, global stats) **only during `fit` on the
training split**. `transform` then maps any row to a fixed-length numeric vector
using those learned parameters, so a validation/test row's features never depend
on other rows in its split — no train/test leakage. Unseen users/categories fall
back to global defaults.

Feature groups: temporal (cyclical hour, off-hours, weekend), amount ratios and
z-scores vs the user and the population, velocity, geo (is-home), and frequency
encodings for category/country.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from statistics import mean, pstdev

from ml.anomaly.data import Transaction

FEATURE_NAMES = [
    "log_amount",
    "amount_ratio_user",
    "amount_z_user",
    "amount_z_global",
    "hour_sin",
    "hour_cos",
    "is_off_hours",
    "day_of_week",
    "is_weekend",
    "log_seconds_since_prev",
    "is_rapid",
    "country_is_home",
    "country_freq",
    "category_freq",
]

_EPS = 1e-6


@dataclass
class FeaturePipeline:
    fitted: bool = False
    user_mean: dict[int, float] = field(default_factory=dict)
    user_std: dict[int, float] = field(default_factory=dict)
    user_home: dict[int, str] = field(default_factory=dict)
    cat_freq: dict[str, float] = field(default_factory=dict)
    country_freq: dict[str, float] = field(default_factory=dict)
    global_mean: float = 0.0
    global_std: float = 1.0

    @property
    def feature_names(self) -> list[str]:
        return list(FEATURE_NAMES)

    def fit(self, rows: list[Transaction]) -> FeaturePipeline:
        """Learn all parameters from the training rows only."""
        by_user_amt: dict[int, list[float]] = defaultdict(list)
        by_user_country: dict[int, Counter] = defaultdict(Counter)
        cat_counter: Counter = Counter()
        country_counter: Counter = Counter()
        amounts: list[float] = []

        for t in rows:
            by_user_amt[t.user_id].append(t.amount)
            by_user_country[t.user_id][t.country] += 1
            cat_counter[t.merchant_category] += 1
            country_counter[t.country] += 1
            amounts.append(t.amount)

        self.user_mean = {u: mean(a) for u, a in by_user_amt.items()}
        self.user_std = {
            u: (pstdev(a) if len(a) > 1 else 0.0) for u, a in by_user_amt.items()
        }
        self.user_home = {u: c.most_common(1)[0][0] for u, c in by_user_country.items()}
        n = len(rows) or 1
        self.cat_freq = {k: v / n for k, v in cat_counter.items()}
        self.country_freq = {k: v / n for k, v in country_counter.items()}
        self.global_mean = mean(amounts) if amounts else 0.0
        self.global_std = pstdev(amounts) if len(amounts) > 1 else 1.0
        self.fitted = True
        return self

    def transform_row(self, t: Transaction) -> list[float]:
        """Map one transaction to a feature vector using learned parameters."""
        um = self.user_mean.get(t.user_id, self.global_mean)
        us = self.user_std.get(t.user_id, self.global_std) or _EPS
        gstd = self.global_std or _EPS

        home = self.user_home.get(t.user_id)
        return [
            math.log1p(t.amount),
            t.amount / um if um else 1.0,
            (t.amount - um) / us,
            (t.amount - self.global_mean) / gstd,
            math.sin(2 * math.pi * t.hour / 24.0),
            math.cos(2 * math.pi * t.hour / 24.0),
            1.0 if 1 <= t.hour <= 5 else 0.0,
            float(t.day_of_week),
            1.0 if t.is_weekend else 0.0,
            math.log1p(max(0.0, t.seconds_since_prev)),
            1.0 if t.seconds_since_prev < 60 else 0.0,
            1.0 if home is not None and t.country == home else 0.0,
            self.country_freq.get(t.country, 0.0),
            self.cat_freq.get(t.merchant_category, 0.0),
        ]

    def transform(self, rows: list[Transaction]) -> list[list[float]]:
        if not self.fitted:
            raise RuntimeError("FeaturePipeline.transform called before fit")
        return [self.transform_row(t) for t in rows]

    def fit_transform(self, rows: list[Transaction]) -> list[list[float]]:
        return self.fit(rows).transform(rows)


def to_xy(
    pipeline: FeaturePipeline, rows: list[Transaction]
) -> tuple[list[list[float]], list[int]]:
    """Feature matrix X and label vector y for a split (pipeline must be fitted)."""
    return pipeline.transform(rows), [t.label for t in rows]
