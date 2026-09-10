"use client";

// Home (second-pass redesign) — agent-first AI workspace.
// Main column: ask bar, greeting, Working now, Your team, Recent tasks.
// Right rail: feature card, Quick actions, Live activity.
// All data is REAL (persisted agents + real runs). Offline is handled cleanly, not with a
// raw developer banner. No fabricated progress/activity.

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { type ActivityEvent, type AgentDTO, listAgents, ownerActivity, runAgent } from "./lib/agentsApi";
import {
  ActiveAgentCard,
  ActivityFeed,
  AgentCard,
  AgentEmptyState,
  AskBar,
  CreateAgentCard,
  MascotTeamStage,
  OfflineState,
  QuickActions,
  RecentTasks,
  StarterPacks,
} from "./components/home/HomeParts";

const ACTIVE = new Set(["thinking", "planning", "working", "waiting", "needs_approval"]);

function greeting(): string {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

export default function Home() {
  const [agents, setAgents] = useState<AgentDTO[] | null>(null);
  const [activity, setActivity] = useState<ActivityEvent[]>([]);
  const [offline, setOffline] = useState(false);

  const load = useCallback(() => {
    listAgents()
      .then((a) => { setAgents(a); setOffline(false); })
      .catch(() => { setAgents([]); setOffline(true); });
    ownerActivity().then(setActivity).catch(() => setActivity([]));
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 6000);
    return () => clearInterval(t);
  }, [load]);

  const run = (id: string) => runAgent(id).then(load).catch(() => {});
  const active = (agents || []).filter((a) => ACTIVE.has(a.status));
  const latestFor = (id: string) => activity.find((e) => e.agent_id === id)?.summary;

  return (
    <div className="home">
      <div className="aui">
        <AskBar />
        <div className="aui-hero">
          <h1>{greeting()}, Gaurav.</h1>
          <p>Your AI team is working for you.</p>
        </div>

        {/* The empty state supplies its own hero, so don't render two banners
            before the user has created their first agent. */}
        {!offline && agents !== null && agents.length > 0 && <MascotTeamStage />}

        {offline ? (
          <OfflineState onRetry={load} />
        ) : agents !== null && agents.length === 0 ? (
          <AgentEmptyState />
        ) : (
          <div className="aui-cols">
            {/* MAIN COLUMN */}
            <div>
              {active.length > 0 && (
                <>
                  <div className="aui-sec-head"><span className="aui-sec-title">Working now</span></div>
                  <div className="aui-active">
                    {active.map((a) => <ActiveAgentCard key={a.id} agent={a} objective={latestFor(a.id)} />)}
                  </div>
                </>
              )}

              <div className="aui-sec-head">
                <div>
                  <div className="aui-sec-title">Your agents</div>
                  <div className="aui-sec-sub">AI workers you&apos;ve created.</div>
                </div>
                <Link href="/agents" className="aui-link">View all →</Link>
              </div>
              <div className="aui-grid">
                {(agents || []).slice(0, 7).map((a) => <AgentCard key={a.id} agent={a} onRun={run} />)}
                <CreateAgentCard />
              </div>

              <RecentTasks events={activity} />
              <StarterPacks />
            </div>

            {/* RIGHT RAIL */}
            <div className="aui-rail">
              <QuickActions />
              <ActivityFeed events={activity} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
