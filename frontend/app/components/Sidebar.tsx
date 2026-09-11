"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import Icon from "./Icon";

const NAV = [
  { href: "/os", label: "Home", icon: "home" },
  { href: "/missions", label: "Missions", icon: "missions" },
  { href: "/agents", label: "Agents", icon: "agents" },
  { href: "/memory", label: "Memory", icon: "memory" },
  { href: "/knowledge", label: "Knowledge", icon: "knowledge" },
  { href: "/tools", label: "Tools", icon: "tools" },
  { href: "/evaluations", label: "Evaluations", icon: "evaluations" },
  { href: "/observability", label: "Observability", icon: "observability" },
];

// Flat list of the seven student-facing AI agents (one entry per real product).
const AGENTS = [
  { href: "/agents/job-search", label: "Job Search Agent", icon: "jobsearch" },
  { href: "/agents/research", label: "Research Agent", icon: "research" },
  { href: "/agents/student-career/resume", label: "Resume Optimizer", icon: "file" },
  { href: "/agents/student-career/sop", label: "SOP Builder", icon: "edit" },
  { href: "/agents/student-career/scholarships", label: "Scholarship Finder", icon: "knowledge" },
  { href: "/agents/student-career/phd", label: "PhD Finder", icon: "cap" },
  { href: "/agents/student-career/interview", label: "Interview Coach", icon: "users" },
];

export default function Sidebar() {
  const path = usePathname();
  const [agentsOpen, setAgentsOpen] = useState(true);
  const active = (href: string) => (href === "/os" ? path === "/os" : path === href);

  // The cinematic landing (World 1) is full-bleed with no control-plane chrome.
  if (path === "/") return null;

  return (
    <aside className="sb">
      <div className="brand">
        <span className="brand-logo"><Icon name="logo" size={15} /></span>
        <span className="brand-name">Agentic AI OS</span>
      </div>

      <nav className="nav">
        {NAV.map((n) => (
          <Link key={n.href} href={n.href} className={`nav-item ${active(n.href) ? "active" : ""}`} title={n.label}>
            <Icon name={n.icon} /><span className="nl">{n.label}</span>
          </Link>
        ))}
      </nav>

      <div className="sec">
        <button className={`sec-h ${agentsOpen ? "" : "collapsed"}`} onClick={() => setAgentsOpen((v) => !v)}>
          AI Agents <Icon name="chevronDown" size={13} sw={2} />
        </button>
        {agentsOpen && (
          <div className="child">
            {AGENTS.map((a) => (
              <Link key={a.href} href={a.href} className={`nav-item ${active(a.href) ? "active" : ""}`} title={a.label}>
                <Icon name={a.icon} /><span className="nl">{a.label}</span>
              </Link>
            ))}
          </div>
        )}
      </div>

      <div className="sb-foot">
        <Link href="/settings" className="nav-item" title="Settings"><Icon name="settings" /><span className="nl">Settings</span></Link>
        <div className="user">
          <span className="avatar">GJ</span>
          <div><b>Gaurav Jha</b><span>Workspace owner</span></div>
        </div>
      </div>
    </aside>
  );
}
