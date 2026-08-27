# Fault-Injection Benchmark (Day 20)

The reproducible source of the reliability numbers on the eval dashboard and
landing page. It generates tasks across eight categories, runs each through the
**real** mission runtime (scheduler + recovery + memory) with injected faults,
and measures genuine outcomes. Nothing is hard-coded; every number falls out of
running the system.

```bash
python -m benchmarks.run --per-category 25 --seed 42 --out artifacts/benchmark
```

## Categories & fault model

| category | subtasks | faults/subtask | stresses |
| --- | --- | --- | --- |
| easy | 2 | 0 | baseline |
| medium | 3 | 1 | single-fault recovery |
| hard | 4 | 2 | double-fault escalation |
| long_horizon | 6 | 0 | many-step missions |
| tool_failure | 3 | 1 | tool error → recovery |
| memory_dependent | 2 | 0 | memory retrieval |
| ambiguous | 2 | 0 | tool misrouting |
| adversarial | 1 | unsafe | safety blocking |

`faults` = transient failures injected per subtask. The runtime recovers a
**single** transient failure (one retry) but escalates a **double** one — so
`hard` deliberately exercises the failure path.

## Metrics

task success, **recovery rate** (of fault-injected tasks), tool-selection
accuracy, memory-retrieval rate, safety block rate, planning validity,
human-intervention rate, average latency, average cost, and success per category.

## Real results (200 tasks, seed 42)

| metric | value |
| --- | --- |
| task success rate | **0.875** |
| recovery rate | **0.667** |
| tool selection accuracy | **0.857** |
| memory retrieval rate | **1.000** |
| safety block rate | **1.000** |
| planning validity | **1.000** |
| human intervention rate | 0.250 |
| avg latency | 0.014 s |
| avg cost | $4e-06 |

Success by category: easy/medium/long_horizon/tool_failure/memory_dependent/
ambiguous/adversarial = 1.0, **hard = 0.0**.

These are honest, reproducible numbers — including the limitation they expose: the
current recovery integration retries once, so double-fault (`hard`) missions
escalate rather than recover, pulling recovery rate to 0.667. That's a real
finding to improve, not a number to inflate.

### Tested

Task generation across all categories, the tool selector and safety check, metric
ranges, the expected fault-model outcomes (easy=1.0, hard=0.0, memory=1.0,
safety=1.0, recovery=2/3), and run-to-run reproducibility.
