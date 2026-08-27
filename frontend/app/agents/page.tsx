export default function Agents() {
  const roles = [
    ["Planner", "Decomposes a goal into a task DAG (subgoals + dependencies)."],
    ["Executor", "Runs each ready task via the tool-use loop."],
    ["Critic / Judge", "Scores output; on rejection triggers a bounded replan."],
    ["Researcher", "Gathers facts and sources for a subtask."],
    ["Analyst", "Reasons over tradeoffs and produces analysis."],
  ];
  return (
    <div className="page">
      <div className="page-head"><div><h1 className="page-title">Agents</h1>
        <p className="page-sub">Role-specialized agents in the mission runtime (see them live in Playground).</p></div></div>
      <div className="card"><h3>Roles</h3>
        <table className="mtable"><tbody>
          {roles.map(([r, d]) => (<tr key={r}><td style={{ width: 160 }}><b>{r}</b></td><td className="muted">{d}</td></tr>))}
        </tbody></table>
      </div>
      <div className="card"><h3>Loop</h3>
        <p className="muted" style={{ margin: 0 }}>Planner → Executor → Critic → (replan) → Finalize, with a bounded retry ladder and per-run cost telemetry.</p></div>
    </div>
  );
}
