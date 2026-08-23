"""Synthetic financial-transaction generator with injected, labeled anomalies.

A real anomaly-detection project needs labeled data; real fraud labels are scarce
and private, so we generate a reproducible synthetic stream. Each user has a home
country and a typical spend; normal transactions are drawn around those, and a
controlled fraction are replaced by one of five labeled anomaly patterns:

- **amount_spike** — an unusually large amount (10-50x the user's norm)
- **velocity** — a transaction seconds after the previous one
- **duplicate** — same amount + merchant as the immediately prior transaction
- **off_hours** — activity in the 1-4am dead zone
- **geo_mismatch** — a country different from the user's home

Everything is seeded, so the same config yields byte-identical data — which is
what makes the downstream training/eval reproducible. This module only *generates
and splits* data; feature engineering is Day 14.
"""
from __future__ import annotations

import math
import random
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

ANOMALY_TYPES = ("amount_spike", "velocity", "duplicate", "off_hours", "geo_mismatch")
NONE = "none"

# A fixed epoch start so timestamps are deterministic across runs.
_BASE_TS = 1_700_000_000.0
_DAY = 86400.0


@dataclass
class Transaction:
    txn_id: int
    user_id: int
    timestamp: float
    amount: float
    merchant_id: int
    merchant_category: str
    country: str
    hour: int
    day_of_week: int
    is_weekend: bool
    seconds_since_prev: float
    label: int          # 0 = normal, 1 = anomaly
    anomaly_type: str   # NONE or one of ANOMALY_TYPES

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class GeneratorConfig:
    n_transactions: int = 5000
    n_users: int = 200
    anomaly_rate: float = 0.06
    seed: int = 42
    categories: tuple[str, ...] = (
        "grocery", "dining", "travel", "electronics", "utilities", "entertainment",
    )
    countries: tuple[str, ...] = ("US", "GB", "DE", "IN", "JP", "BR")


FEATURE_FIELDS = (
    "amount", "merchant_category", "country", "hour", "day_of_week",
    "is_weekend", "seconds_since_prev",
)


def _hour_dow(ts: float) -> tuple[int, int]:
    dt = datetime.fromtimestamp(ts, tz=UTC)
    return dt.hour, dt.weekday()


def generate(config: GeneratorConfig | None = None) -> list[Transaction]:
    """Generate a reproducible list of labeled transactions."""
    cfg = config or GeneratorConfig()
    rng = random.Random(cfg.seed)

    users = {}
    for uid in range(cfg.n_users):
        users[uid] = {
            "home": rng.choice(cfg.countries),
            "mu": rng.uniform(2.5, 4.5),   # amounts ~ exp(N(mu, sigma))
            "sigma": 0.5,
            "last_ts": _BASE_TS + rng.uniform(0, _DAY),
            "last_amount": None,
            "last_merchant": None,
        }

    rows: list[Transaction] = []
    for i in range(cfg.n_transactions):
        uid = rng.randrange(cfg.n_users)
        u = users[uid]

        gap = rng.uniform(300, 3 * 3600)         # 5 min .. 3 h between txns
        ts = u["last_ts"] + gap
        amount = round(math.exp(rng.gauss(u["mu"], u["sigma"])), 2)
        category = rng.choice(cfg.categories)
        merchant = rng.randrange(1000, 9999)
        country = u["home"]
        seconds_since_prev = ts - u["last_ts"]
        label, anomaly_type = 0, NONE

        if rng.random() < cfg.anomaly_rate:
            label = 1
            anomaly_type = rng.choice(ANOMALY_TYPES)
            if anomaly_type == "duplicate" and u["last_amount"] is None:
                anomaly_type = "amount_spike"  # no prior txn to duplicate yet

            if anomaly_type == "amount_spike":
                amount = round(amount * rng.uniform(10, 50), 2)
            elif anomaly_type == "velocity":
                seconds_since_prev = rng.uniform(1, 20)
                ts = u["last_ts"] + seconds_since_prev
            elif anomaly_type == "duplicate":
                amount = u["last_amount"]
                merchant = u["last_merchant"]
                seconds_since_prev = rng.uniform(5, 60)
                ts = u["last_ts"] + seconds_since_prev
            elif anomaly_type == "geo_mismatch":
                country = rng.choice([c for c in cfg.countries if c != u["home"]])

        hour, dow = _hour_dow(ts)
        if anomaly_type == "off_hours":
            hour = rng.randint(1, 4)  # force the dead-zone hour (the modeled feature)

        rows.append(Transaction(
            txn_id=i, user_id=uid, timestamp=ts, amount=amount,
            merchant_id=merchant, merchant_category=category, country=country,
            hour=hour, day_of_week=dow, is_weekend=dow >= 5,
            seconds_since_prev=seconds_since_prev, label=label,
            anomaly_type=anomaly_type,
        ))
        u["last_ts"], u["last_amount"], u["last_merchant"] = ts, amount, merchant

    return rows


@dataclass
class Splits:
    train: list[Transaction] = field(default_factory=list)
    val: list[Transaction] = field(default_factory=list)
    test: list[Transaction] = field(default_factory=list)


def split(
    rows: list[Transaction],
    ratios: tuple[float, float, float] = (0.7, 0.15, 0.15),
    seed: int = 42,
) -> Splits:
    """Stratified train/val/test split — label balance preserved across splits."""
    rng = random.Random(seed)
    pos = [r for r in rows if r.label == 1]
    neg = [r for r in rows if r.label == 0]
    rng.shuffle(pos)
    rng.shuffle(neg)

    def cut(lst: list[Transaction]) -> tuple[list, list, list]:
        n = len(lst)
        a = int(n * ratios[0])
        b = int(n * (ratios[0] + ratios[1]))
        return lst[:a], lst[a:b], lst[b:]

    ptr, pva, pte = cut(pos)
    ntr, nva, nte = cut(neg)
    out = Splits(train=ptr + ntr, val=pva + nva, test=pte + nte)
    for part in (out.train, out.val, out.test):
        rng.shuffle(part)
    return out


def dataset_card(rows: list[Transaction], config: GeneratorConfig) -> dict:
    """Summary stats describing the dataset (counts, balance, type mix, schema)."""
    n = len(rows)
    n_pos = sum(r.label for r in rows)
    types = Counter(r.anomaly_type for r in rows if r.label == 1)
    return {
        "n_transactions": n,
        "n_users": config.n_users,
        "seed": config.seed,
        "anomaly_rate_target": config.anomaly_rate,
        "anomaly_rate_actual": round(n_pos / n, 4) if n else 0.0,
        "n_anomalies": n_pos,
        "anomaly_type_counts": dict(sorted(types.items())),
        "feature_fields": list(FEATURE_FIELDS),
    }
