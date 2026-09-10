"use client";

// Reusable Home building blocks (second-pass redesign). Presentation only — every
// component receives REAL data from the caller; none fabricate agents, progress or activity.

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import AgentCharacter from "../AgentCharacter";
import { type AgentState, STATE_LABEL } from "../../lib/characters";
import type { ActivityEvent, AgentDTO } from "../../lib/agentsApi";

export function timeAgo(ts: number): string {
  const s = Math.max(0, Date.now() / 1000 - ts);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

// --- command / ask bar -------------------------------------------------------
export function AskBar() {
  const router = useRouter();
  const [q, setQ] = useState("");
  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (q.trim()) router.push(`/agents/new?desc=${encodeURIComponent(q.trim())}`);
  }
  return (
    <div>
      <form className="aui-cmd" onSubmit={submit}>
        <AgentCharacter character="nova" state="idle" size={34} />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask your agents anything…" aria-label="Ask your agents anything" />
        <span className="aui-kbd">⌘K</span>
      </form>
      <div className="aui-cmd-sub">…or describe a new agent and press Enter.</div>
    </div>
  );
}

// --- active agent workspace card --------------------------------------------
export function ActiveAgentCard({ agent, objective }: { agent: AgentDTO; objective?: string }) {
  return (
    <div className="aui-work">
      <div className="aui-char-wrap"><AgentCharacter character={agent.character_id} state={agent.status as AgentState} size={104} /></div>
      <div className="aui-work-name">{agent.name}</div>
      <div className="aui-work-line">{STATE_LABEL[agent.status as AgentState] || agent.status}…</div>
      <div className="aui-panel">
        <div className="aui-panel-row"><span>{agent.purpose ? "Current task" : "Task"}</span><span>{STATE_LABEL[agent.status as AgentState]}</span></div>
        <div className="aui-panel-obj">{objective || agent.purpose || agent.description || "—"}</div>
        <div className="aui-bar"><i /></div>
      </div>
    </div>
  );
}

// --- your-agents card + create card -----------------------------------------
export function AgentCard({ agent, onRun }: { agent: AgentDTO; onRun: (id: string) => void }) {
  const active = agent.status !== "idle" && agent.status !== "paused";
  return (
    <div className="aui-card">
      <div className="aui-char-top">
        <AgentCharacter character={agent.character_id} state={(agent.status as AgentState) || "idle"} size={64} />
        <button className="aui-arrow" title="Run task" aria-label={`Run ${agent.name}`} onClick={() => onRun(agent.id)}>▸</button>
      </div>
      <div className="aui-card-name">{agent.name}</div>
      <div className="aui-card-purpose">{agent.purpose || agent.description || "—"}</div>
      <div className="aui-card-foot">
        <span className={`aui-dot ${active ? "on" : ""}`}>{STATE_LABEL[agent.status as AgentState] || agent.status}</span>
        <span className="aui-task-time">{agent.last_run_at ? timeAgo(agent.last_run_at) : "new"}</span>
      </div>
    </div>
  );
}

export function CreateAgentCard() {
  return (
    <Link href="/agents/new" className="aui-card aui-create">
      <div className="aui-plus">+</div>
      <div className="aui-card-name">Create agent</div>
      <div className="aui-card-purpose" style={{ flex: "none" }}>Give a new AI worker a job.</div>
    </Link>
  );
}

// --- quick actions -----------------------------------------------------------
export function QuickActions() {
  const items = [
    { href: "/agents/new", ic: "+", label: "Create a new agent" },
    { href: "/missions", ic: "▶", label: "Create a new task" },
    { href: "/knowledge", ic: "↑", label: "Upload a document" },
    { href: "/knowledge", ic: "◎", label: "Ask my knowledge base" },
    { href: "/missions", ic: "⚡", label: "Run a workflow" },
  ];
  return (
    <div className="aui-rail-card">
      <div className="aui-rail-title">Quick actions</div>
      <div className="aui-qa">
        {items.map((i, k) => (
          <Link key={k} href={i.href}><span className="ic">{i.ic}</span>{i.label}</Link>
        ))}
      </div>
    </div>
  );
}

// --- live activity -----------------------------------------------------------
export function ActivityFeed({ events }: { events: ActivityEvent[] }) {
  return (
    <div className="aui-rail-card">
      <div className="aui-rail-title">Live activity <span className="aui-live">Live</span></div>
      {events.length === 0 ? (
        <div className="aui-empty-note">No agent activity yet.</div>
      ) : (
        <div className="aui-feed">
          {events.slice(0, 6).map((e, i) => (
            <div key={i} className="aui-feed-row">
              <AgentCharacter character={e.character_id} state={e.status === "completed" ? "completed" : e.status === "failed" ? "failed" : "working"} size={30} />
              <div className="aui-feed-body">
                <div className="aui-feed-name">{e.agent_name}</div>
                <div className="aui-feed-sum">{e.summary}</div>
              </div>
              <div className="aui-feed-time">{timeAgo(e.at)}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// --- recent tasks ------------------------------------------------------------
const TASK_STATUS_LABEL: Record<string, string> = {
  created: "Not started", active: "In progress", paused: "Paused", completed: "Done", failed: "Failed",
};
export function RecentTasks({ events }: { events: ActivityEvent[] }) {
  if (events.length === 0) return null;
  return (
    <div style={{ marginTop: 30 }}>
      <div className="aui-sec-head"><span className="aui-sec-title">Recent tasks</span></div>
      <div className="aui-tasks">
        {events.slice(0, 6).map((e, i) => (
          <div key={i} className="aui-task">
            <span className="aui-check" />
            <AgentCharacter character={e.character_id} state="idle" size={26} />
            <span className="aui-task-name">{e.summary}</span>
            <span className="aui-task-status">{TASK_STATUS_LABEL[e.status] || e.status}</span>
            <span className="aui-task-time">{timeAgo(e.at)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// --- feature / brand card ----------------------------------------------------
export function FeatureCard() {
  const chars = ["nova", "milo", "luna", "coco", "rory"];
  return (
    <Link href="/agents" className="aui-rail-card aui-feature">
      <img className="aui-feature-art" src="/mascots/team-hero.webp" alt="" />
      <div className="aui-feature-row">
        {chars.map((c) => <span key={c}><AgentCharacter character={c} state="idle" size={38} /></span>)}
      </div>
      <h3>Small agents. Big progress.</h3>
      <p>Build a team of specialists that remember, decide and get real work done.</p>
      <span className="aui-btn">Meet the team</span>
    </Link>
  );
}

// --- empty + offline ---------------------------------------------------------
export function AgentEmptyState() {
  return (
    <>
      <section className="aui-empty aui-team-stage">
        <div className="aui-stage-copy">
          <span className="aui-stage-kicker">Your AI team</span>
          <h2>Small agents.<br />Big progress.</h2>
          <p>Give each agent a job and they&apos;ll plan, remember, and work together for you.</p>
          <Link href="/agents/new" className="aui-btn">Create your first agent <span>→</span></Link>
        </div>
        <div className="aui-stage-art" aria-hidden="true">
          <img src="/mascots/team-hero.webp" alt="" />
          <div className="aui-stage-orbit orbit-a" />
          <div className="aui-stage-orbit orbit-b" />
        </div>
        <div className="aui-stage-roster" aria-label="Available agent characters">
          {["peter", "ivy", "rory", "luna", "echo", "momo", "atlas", "coco", "nori", "pip"].map((c, index) => (
            <span key={c} style={{ animationDelay: `${index * 110}ms` }}><AgentCharacter character={c} state="idle" size={42} /></span>
          ))}
        </div>
      </section>

      <section className="aui-spotlight" aria-labelledby="meet-team-title">
        <div className="aui-spotlight-copy">
          <span className="aui-stage-kicker">Meet the crew · 01</span>
          <h2 id="meet-team-title">Hey, I&apos;m Prospect Peter.</h2>
          <p>I&apos;m your opportunity scout. Give me a goal and I&apos;ll hunt for jobs, leads, people, and the next smart move.</p>
          <div className="aui-spotlight-pills"><span>✦ finds opportunities</span><span>✦ drafts outreach</span><span>✦ keeps you moving</span></div>
          <Link href="/agents/new?desc=Find%20the%20best%20opportunities%20for%20me" className="aui-btn">Work with Peter <span>→</span></Link>
        </div>
        <div className="aui-spotlight-art" aria-hidden="true">
          <div className="aui-hand-note">This is Peter!<br />He&apos;s ready to help.</div>
          <div className="aui-hand-arrow">⤵</div>
          <img src="/mascots/peter-3d.webp" alt="" />
        </div>
      </section>

      <section className="aui-spotlight aui-spotlight-reverse aui-spotlight-ivy" aria-labelledby="ivy-title">
        <div className="aui-spotlight-copy">
          <span className="aui-stage-kicker">Meet the crew · 02</span>
          <h2 id="ivy-title">Hi, I&apos;m Invoice Ivy.</h2>
          <p>I make money admin feel easy. Hand me invoices, receipts, or a budget and I&apos;ll turn the chaos into clean next steps.</p>
          <div className="aui-spotlight-pills"><span>✦ reads invoices</span><span>✦ spots details</span><span>✦ organizes budgets</span></div>
          <Link href="/agents/new?desc=Organize%20my%20invoices%20and%20budget" className="aui-btn">Work with Ivy <span>→</span></Link>
        </div>
        <div className="aui-spotlight-art" aria-hidden="true">
          <div className="aui-hand-note">This is Ivy!<br />She loves a tidy total.</div>
          <div className="aui-hand-arrow">⤵</div>
          <img src="/mascots/ivy-3d.webp" alt="" />
        </div>
      </section>

      <section className="aui-spotlight aui-spotlight-rory" aria-labelledby="rory-title">
        <div className="aui-spotlight-copy">
          <span className="aui-stage-kicker">Meet the crew · 03</span>
          <h2 id="rory-title">Hey, I&apos;m Research Rory.</h2>
          <p>Send the long reads my way. I explore papers, sources, and tabs, then bring back the ideas that actually matter.</p>
          <div className="aui-spotlight-pills"><span>✦ explores sources</span><span>✦ summarizes fast</span><span>✦ cites the good stuff</span></div>
          <Link href="/agents/new?desc=Research%20and%20summarize%20this%20topic" className="aui-btn">Work with Rory <span>→</span></Link>
        </div>
        <div className="aui-spotlight-art" aria-hidden="true">
          <div className="aui-hand-note">Rory is curious<br />about everything.</div>
          <div className="aui-hand-arrow">⤵</div>
          <img src="/mascots/rory-3d.webp" alt="" />
        </div>
      </section>

      <section className="aui-spotlight aui-spotlight-reverse aui-spotlight-luna" aria-labelledby="luna-title">
        <div className="aui-spotlight-copy">
          <span className="aui-stage-kicker">Meet the crew · 04</span>
          <h2 id="luna-title">Hello, I&apos;m Luna.</h2>
          <p>I&apos;m your academic-path guide. I help find programs, labs, scholarships, and the next place your big idea can grow.</p>
          <div className="aui-spotlight-pills"><span>✦ finds programs</span><span>✦ maps funding</span><span>✦ tracks deadlines</span></div>
          <Link href="/agents/new?desc=Find%20PhD%20programs%20and%20funding%20for%20me" className="aui-btn">Work with Luna <span>→</span></Link>
        </div>
        <div className="aui-spotlight-art" aria-hidden="true">
          <div className="aui-hand-note">Luna sees the<br />path ahead.</div>
          <div className="aui-hand-arrow">⤵</div>
          <img src="/mascots/luna-3d.webp" alt="" />
        </div>
      </section>

      <section className="aui-how" aria-labelledby="how-title">
        <div className="aui-how-copy"><span className="aui-stage-kicker">How it works</span><h2 id="how-title">You describe it. We match the vibe.</h2><p>Start in plain language—your agent gets the character and tools that fit the work.</p></div>
        <div className="aui-how-steps">
          <div><b>01</b><span>Tell us the job</span><small>“Find PhD programs in AI”</small></div>
          <div><b>02</b><span>Meet the match</span><small>Luna joins as your research guide</small></div>
          <div><b>03</b><span>Watch it float</span><small>Your team plans, remembers, and works</small></div>
        </div>
        <Link href="/agents/new" className="aui-btn">Make my first agent <span>→</span></Link>
      </section>

      <section className="aui-crew-next" aria-labelledby="crew-next-title">
        <div><span className="aui-stage-kicker">The rest of the crew</span><h2 id="crew-next-title">Different agents. Different things. Better together.</h2></div>
        <p>Next up: Ivy keeps money organized, Rory goes deep on research, Luna finds academic paths, Echo makes data useful, and Momo handles the inbox. Create any agent in your own words and the right character joins your team.</p>
        <Link href="/agents/new" className="aui-btn ghost">Meet your match <span>→</span></Link>
      </section>
    </>
  );
}

// Always-visible home showcase: the workspace should feel alive even before
// an agent has a current task or the API has returned a populated roster.
export function MascotTeamStage() {
  return (
    <section className="aui-team-stage aui-team-stage-home">
      <div className="aui-stage-copy">
        <span className="aui-stage-kicker">Your AI team</span>
        <h2>Small agents.<br />Big progress.</h2>
        <p>Each agent has a specialty. Create one in plain language and we&apos;ll match it with a character for the work.</p>
        <Link href="/agents/new" className="aui-btn">Create an agent <span>→</span></Link>
      </div>
      <div className="aui-stage-art" aria-hidden="true">
        <img src="/mascots/team-hero.webp" alt="" />
        <div className="aui-stage-orbit orbit-a" />
        <div className="aui-stage-orbit orbit-b" />
      </div>
      <div className="aui-stage-roster" aria-label="Available agent characters">
        {["peter", "ivy", "rory", "luna", "echo", "momo", "atlas", "coco", "nori", "pip"].map((c, index) => (
          <span key={c} style={{ animationDelay: `${index * 110}ms` }}><AgentCharacter character={c} state="idle" size={42} /></span>
        ))}
      </div>
    </section>
  );
}

export function StarterPacks() {
  const packs = [
    { character: "peter", eyebrow: "Career mode", title: "Find your next big thing", copy: "Jobs, internships, and opportunities—filtered for your vibe.", href: "/agents/new?desc=Find%20the%20best%20AI%20jobs%20for%20me", tone: "blue", cta: "Start scouting" },
    { character: "rory", eyebrow: "Study sprint", title: "Turn tabs into takeaways", copy: "Research, papers, and citations without the information overload.", href: "/agents/new?desc=Research%20and%20summarize%20new%20AI%20papers", tone: "orange", cta: "Go deep" },
    { character: "echo", eyebrow: "Data glow-up", title: "Make numbers make sense", copy: "Drop in a spreadsheet and get clear, useful answers back.", href: "/agents/new?desc=Analyze%20my%20spreadsheet%20and%20find%20insights", tone: "mint", cta: "Analyze it" },
  ];
  return (
    <section className="aui-packs">
      <div className="aui-packs-head"><div><span className="aui-stage-kicker">Start here</span><h2>Pick a vibe. Make progress.</h2></div><span className="aui-packs-spark">✦ made for your flow</span></div>
      <div className="aui-pack-grid">
        {packs.map((pack) => (
          <Link key={pack.title} href={pack.href} className={`aui-pack ${pack.tone}`}>
            <span className="aui-pack-orb" />
            <div className="aui-pack-top"><AgentCharacter character={pack.character} state="thinking" size={68} /><span className="aui-pack-tag">{pack.eyebrow}</span></div>
            <h3>{pack.title}</h3><p>{pack.copy}</p><span className="aui-pack-cta">{pack.cta} <b>→</b></span>
          </Link>
        ))}
      </div>
    </section>
  );
}

export function OfflineState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="aui-offline">
      <AgentCharacter character="luna" state="waiting" size={72} />
      <h2 style={{ margin: "10px 0 2px", fontSize: 18 }}>Your agents are resting</h2>
      <p className="aui-cmd-sub" style={{ margin: "2px 0 16px" }}>The agent service is temporarily offline.</p>
      <button className="aui-btn ghost" onClick={onRetry}>Retry</button>
    </div>
  );
}
