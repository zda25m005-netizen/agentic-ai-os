"use client";
import Icon from "../Icon";
import { BENCHMARK, EvalMetric, pct, status, STATUS_LABEL } from "../../lib/evalData";

export default function EvalDetailDrawer({ metric, onClose }: { metric: EvalMetric; onClose: () => void }) {
  const s = status(metric);
  const failedApprox = Math.round((1 - metric.score) * BENCHMARK.tasks);
  return (
    <>
      <div className="scrim" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-label={`${metric.name} detail`}>
        <div className="dh">
          <div>
            <div className="d-eyebrow">Evaluation Metric</div>
            <div className="d-name">{metric.name}</div>
          </div>
          <button className="dclose" onClick={onClose} aria-label="Close"><Icon name="x" size={16} /></button>
        </div>

        <div className="kv">
          <span className="k">Score</span><span className="v">{pct(metric.score)}</span>
          <span className="k">Target</span><span className="v">≥ {pct(metric.target)}</span>
          <span className="k">Status</span>
          <span className="v"><span className={`stpill st ${s}`}><span className="d" />{STATUS_LABEL[s]}</span></span>
          <span className="k">Benchmark</span><span className="v">{BENCHMARK.tasks} tasks · seed {BENCHMARK.seed}</span>
          <span className="k">Approx. misses</span><span className="v">{failedApprox} / {BENCHMARK.tasks}</span>
        </div>

        <div className="d-eyebrow" style={{ marginBottom: 6 }}>Interpretation</div>
        <p className="note" style={{ marginBottom: 16 }}>{metric.interpretation}.</p>

        {metric.note && (
          <>
            <div className="d-eyebrow" style={{ marginBottom: 6 }}>Finding</div>
            <p className="note" style={{ marginBottom: 16 }}>{metric.note}</p>
          </>
        )}

        <p className="note">
          Per-case results (scenario, expected vs observed) are produced by running the benchmark:
          <br /><code>python -m benchmarks.run</code>. Detailed execution traces live in Observability.
        </p>
      </aside>
    </>
  );
}
