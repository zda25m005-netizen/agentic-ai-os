"""Experiment tracking with one interface, two backends.

Uses **MLflow** when it's installed (params/metrics/artifacts logged to the
MLflow store). Otherwise it falls back to a **local JSON** store under
`artifacts/anomaly/runs/`, so training is still fully tracked and reproducible in
CI without the heavy dependency.
"""
from __future__ import annotations

import json
import time
from contextlib import contextmanager
from pathlib import Path


class _Run:
    def __init__(self, name: str):
        self.name = name
        self.params: dict = {}
        self.metrics: dict = {}

    def log_params(self, params: dict) -> None:
        self.params.update(params)

    def log_metrics(self, metrics: dict) -> None:
        self.metrics.update(metrics)


class Tracker:
    def __init__(self, experiment: str = "anomaly", out: str = "artifacts/anomaly/runs"):
        self.experiment = experiment
        self.out = Path(out)
        self.runs: list[_Run] = []  # kept in-memory for inspection/tests
        try:
            import mlflow  # noqa: F401
            self._mlflow = mlflow
            mlflow.set_experiment(experiment)
        except Exception:
            self._mlflow = None

    @property
    def backend(self) -> str:
        return "mlflow" if self._mlflow else "local-json"

    @contextmanager
    def run(self, name: str):
        run = _Run(name)
        if self._mlflow:
            with self._mlflow.start_run(run_name=name):
                yield run
                self._mlflow.log_params(run.params)
                self._mlflow.log_metrics(run.metrics)
        else:
            yield run
            self.out.mkdir(parents=True, exist_ok=True)
            path = self.out / f"{name}-{int(time.time()*1000)}.json"
            path.write_text(json.dumps(
                {"experiment": self.experiment, "name": name,
                 "params": run.params, "metrics": run.metrics}, indent=2))
        self.runs.append(run)
