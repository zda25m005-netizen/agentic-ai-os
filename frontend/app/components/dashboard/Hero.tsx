"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Icon from "../Icon";
import { QUICK_ACTIONS } from "../../lib/dashboardData";

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

export default function Hero({ running = 0 }: { running?: number }) {
  const [goal, setGoal] = useState("");
  const router = useRouter();
  const submit = () => {
    const q = goal.trim();
    router.push(q ? `/missions?goal=${encodeURIComponent(q)}` : "/missions");
  };

  return (
    <>
      <h1 className="h1 fade-up">{greeting()}, Gaurav</h1>
      <p className="h-sub fade-up" style={{ animationDelay: "40ms" }}>
        What would you like to accomplish today?
      </p>

      <div className="hero-grid fade-up" style={{ animationDelay: "80ms" }}>
        <div className="cmd">
          <input
            className="cmd-input"
            placeholder="Describe your goal or task..."
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()}
          />
          <div className="cmd-row">
            {QUICK_ACTIONS.map((a) => (
              <button key={a} className="pill" onClick={() => setGoal(a + " ")}>{a}</button>
            ))}
            <button className="cmd-submit" onClick={submit} aria-label="Start">
              <Icon name="arrowRight" size={16} sw={2} />
            </button>
          </div>
          <div className="cmd-hint">
            <span>Describe an outcome — the OS plans a mission, coordinates agents, and returns a verified result.</span>
            <span className="kbd">⏎ to start</span>
          </div>
        </div>

        <div className="status">
          <h3 className="card-h">System Status</h3>
          <div className="st-row">
            <span className="dot" /><span className="lbl">Agents Online</span>
            <span className="val ok">12 / 12</span>
          </div>
          <div className="st-row">
            <Icon name="running" size={15} /><span className="lbl">Missions Running</span>
            <span className="val">{running}</span>
          </div>
          <div className="st-row">
            <Icon name="sync" size={15} /><span className="lbl">Knowledge Sync</span>
            <span className="val ok">Up to date</span>
          </div>
          <Link href="/observability" className="st-btn">
            View Observability <Icon name="arrowRight" size={13} sw={2} />
          </Link>
        </div>
      </div>
    </>
  );
}
