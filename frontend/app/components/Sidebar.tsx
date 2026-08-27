"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type Item = { href: string; label: string };
type Group = { title?: string; items: Item[] };

const NAV: Group[] = [
  {
    items: [
      { href: "/", label: "Overview" },
      { href: "/workspace", label: "Mission Workspace" },
      { href: "/missions", label: "Missions" },
      { href: "/playground", label: "Playground" },
    ],
  },
  {
    title: "Intelligence",
    items: [
      { href: "/agents", label: "Agents" },
      { href: "/memory", label: "Memory" },
      { href: "/knowledge", label: "Knowledge" },
      { href: "/tools", label: "Tools" },
    ],
  },
  {
    title: "Evaluation",
    items: [
      { href: "/evaluations", label: "Evaluations" },
      { href: "/experiments", label: "Experiments" },
    ],
  },
  {
    title: "Operations",
    items: [
      { href: "/observability", label: "Observability" },
      { href: "/security", label: "Security" },
    ],
  },
];

export default function Sidebar() {
  const path = usePathname();
  const active = (href: string) => (href === "/" ? path === "/" : path.startsWith(href));

  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-dot" />
        <div>
          <div className="brand-name">Agentic AI OS</div>
          <div className="brand-sub">control plane</div>
        </div>
      </div>
      <nav className="nav">
        {NAV.map((g, i) => (
          <div key={i} className="nav-group">
            {g.title && <div className="nav-title">{g.title}</div>}
            {g.items.map((n) => (
              <Link key={n.href} href={n.href} className={`nav-item ${active(n.href) ? "active" : ""}`}>
                {n.label}
              </Link>
            ))}
          </div>
        ))}
      </nav>
      <div className="sidebar-foot">v2 · mission runtime</div>
    </aside>
  );
}
