"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import Icon from "./Icon";

const NAV = [
  { href: "/", label: "Home", icon: "home" },
  { href: "/missions", label: "Missions", icon: "missions" },
  { href: "/agents", label: "Agents", icon: "agents" },
  { href: "/memory", label: "Memory", icon: "memory" },
  { href: "/knowledge", label: "Knowledge", icon: "knowledge" },
  { href: "/tools", label: "Tools", icon: "tools" },
  { href: "/evaluations", label: "Evaluations", icon: "evaluations" },
  { href: "/observability", label: "Observability", icon: "observability" },
];

const AGENTS = [
  { href: "/agents/job-search", label: "Job Search Agent", icon: "jobsearch" },
  { href: "/agents/research", label: "Research Agent", icon: "research" },
  { href: "/agents/knowledge", label: "Personal Knowledge Agent", icon: "person" },
  { href: "/agents/student-career", label: "Student Career Agent", icon: "cap", expandable: true },
  { href: "/agents/browser", label: "Browser / Action Agent", icon: "globe" },
];

const CAREER = [
  { href: "/agents/student-career/job-hunter", label: "Job Hunter" },
  { href: "/agents/student-career/research", label: "Research Agent" },
  { href: "/agents/student-career/resume", label: "Resume Optimizer" },
  { href: "/agents/student-career/sop", label: "SOP Builder" },
  { href: "/agents/student-career/scholarships", label: "Scholarship Finder" },
  { href: "/agents/student-career/phd", label: "PhD Finder" },
  { href: "/agents/student-career/interview", label: "Interview Coach" },
  { href: "/agents/student-career/courses", label: "Course Finder" },
  { href: "/agents/student-career/paper-reviewer", label: "Paper Reviewer" },
  { href: "/agents/student-career/citation-checker", label: "Citation Checker" },
];

export default function Sidebar() {
  const path = usePathname();
  const [agentsOpen, setAgentsOpen] = useState(true);
  const [careerOpen, setCareerOpen] = useState(false);
  const active = (href: string) => (href === "/" ? path === "/" : path === href);

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
              <div key={a.href}>
                <Link href={a.href} className={`nav-item ${active(a.href) ? "active" : ""}`} title={a.label}
                  onClick={a.expandable ? (e) => { e.preventDefault(); setCareerOpen((v) => !v); } : undefined}>
                  <Icon name={a.icon} /><span className="nl">{a.label}</span>
                </Link>
                {a.expandable && careerOpen && (
                  <div className="subchild">
                    {CAREER.map((c) => (
                      <Link key={c.href} href={c.href} className={`nav-item ${active(c.href) ? "active" : ""}`}>
                        {c.label}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
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
