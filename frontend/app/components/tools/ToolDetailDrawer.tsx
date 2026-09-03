"use client";
import Link from "next/link";
import Icon from "../Icon";
import { ToolView } from "../../lib/toolsApi";

const AGENT_HREF: Record<string, string> = {
  "Research Agent": "/agents/research",
  "Job Search Agent": "/agents/job-search",
  "Personal Knowledge Agent": "/agents/knowledge",
  "Student Career Agent": "/agents/student-career",
  "Browser / Action Agent": "/agents/browser",
};

export default function ToolDetailDrawer({ tool, onClose }: { tool: ToolView; onClose: () => void }) {
  return (
    <>
      <div className="scrim" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-label={`${tool.displayName} details`}>
        <div className="dh">
          <div className="dh-left">
            <span className="tool-ico"><Icon name={tool.icon} size={17} sw={1.7} /></span>
            <div>
              <div className="d-eyebrow">Tool · {tool.category}</div>
              <div className="d-name">{tool.displayName}</div>
              <div className="tool-id">{tool.id}</div>
            </div>
          </div>
          <button className="dclose" onClick={onClose} aria-label="Close"><Icon name="x" size={16} /></button>
        </div>

        <div className="sec">
          <div className="sec-lbl">Description</div>
          <p>{tool.description}</p>
        </div>

        <div className="sec">
          <div className="sec-lbl">Status</div>
          <span className={`status ${tool.status}`}><span className="d" />{tool.status[0].toUpperCase() + tool.status.slice(1)}</span>
        </div>

        <div className="sec">
          <div className="sec-lbl">Safety</div>
          <div className="pills">{tool.safety.map((s) => <span className="pill" key={s}>{s}</span>)}</div>
        </div>

        <div className="sec">
          <div className="sec-lbl">Available to</div>
          <div className="pills">
            {tool.agents.map((a) => (
              AGENT_HREF[a]
                ? <Link key={a} href={AGENT_HREF[a]} className="pill">{a}</Link>
                : <span key={a} className="pill">{a}</span>
            ))}
          </div>
        </div>

        <div className="sec">
          <div className="sec-lbl">Usage</div>
          <div className="note">
            Execution telemetry isn’t connected yet. Detailed runs, latency and errors
            live in <Link href="/observability">Observability</Link>.
          </div>
        </div>

        <div className="sec">
          <div className="sec-lbl">Invocation</div>
          <div className="note">
            Registered in the tool registry and invoked by agents during missions —
            not run directly from this page.
          </div>
        </div>
      </aside>
    </>
  );
}
