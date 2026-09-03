"use client";

import { useState } from "react";
import "../evaluations.css";
import BenchmarkSummary from "../components/eval/BenchmarkSummary";
import BenchmarkTable from "../components/eval/BenchmarkTable";
import EvaluationBreakdown from "../components/eval/EvaluationBreakdown";
import FailureAnalysis from "../components/eval/FailureAnalysis";
import ReleaseReadiness from "../components/eval/ReleaseReadiness";
import EvalDetailDrawer from "../components/eval/EvalDetailDrawer";
import { BENCHMARK, EvalMetric } from "../lib/evalData";

export default function EvaluationsPage() {
  const [open, setOpen] = useState<EvalMetric | null>(null);

  return (
    <div className="ev">
      <div className="wrap">
        <div className="head">
          <div>
            <h1 className="h1">Evaluations</h1>
            <p className="h-sub">Measure agent reliability, safety, planning, recovery, and tool-use quality.</p>
          </div>
          <div className="head-actions">
            <span className="badge-fi">Fault Injection · {BENCHMARK.tasks} tasks · seed {BENCHMARK.seed}</span>
          </div>
        </div>

        <BenchmarkSummary />

        <div className="sec-h">Benchmark Results</div>
        <BenchmarkTable onOpen={setOpen} />

        <div className="grid2" style={{ marginTop: 16 }}>
          <div>
            <div className="sec-h" style={{ marginTop: 0 }}>Breakdown</div>
            <EvaluationBreakdown />
          </div>
          <div>
            <div className="sec-h" style={{ marginTop: 0 }}>Failure Analysis</div>
            <FailureAnalysis />
          </div>
        </div>

        <div className="sec-h">Release Readiness</div>
        <ReleaseReadiness />

        <div className="grid2" style={{ marginTop: 16 }}>
          <div className="card">
            <div className="sec-h" style={{ margin: "0 0 10px" }}>Benchmark Quality</div>
            <p className="note" style={{ marginTop: 0 }}>
              {BENCHMARK.tasks} tasks · seed {BENCHMARK.seed} · fully reproducible. These are real
              fault-injection results — recovery is honestly {`${(BENCHMARK.metrics.find((m) => m.id === "recovery")!.score * 100).toFixed(1)}`}%
              because hard double-fault tasks escalate rather than recover. Reproduce with{" "}
              <code>python -m benchmarks.run</code>.
            </p>
          </div>
          <div className="card">
            <div className="sec-h" style={{ margin: "0 0 10px" }}>Evaluation History</div>
            <p className="note" style={{ marginTop: 0 }}>
              No previous runs available. Run history isn’t stored via an API yet — when it is, this
              panel will chart success/recovery trends across runs.
            </p>
          </div>
        </div>
      </div>

      {open && <EvalDetailDrawer metric={open} onClose={() => setOpen(null)} />}
    </div>
  );
}
