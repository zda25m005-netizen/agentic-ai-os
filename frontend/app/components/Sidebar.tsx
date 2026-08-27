"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// Control-plane navigation. Sections that are wired to live data today are
// active; the rest are placeholders on the roadmap (Days 26–30) and marked so.
const NAV: { href: string; label: string; soon?: boolean }[] = [
  { href: "/", label: "Overview" },
  { href: "/workspace", label: "Mission Workspace" },
  { href: "/missions", label: "Missions" },
  { href: "/playground", label: "Playground" },
  { href: "/agents", label: "Agents", soon: true },
  { href: "/memory", label: "Memory", soon: true },
  { href: "/evaluations", label: "Evaluations", soon: true },
  { href: "/observability", label: "Observability", soon: true },
];

export default function Sidebar() {
  const path = usePathname();

  function active(href: string) {
    if (href === "/") return path === "/";
    return path.startsWith(href);
  }

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
        {NAV.map((n) =>
          n.soon ? (
            <span key={n.href} className="nav-item soon" title="Coming soon">
              {n.label}
              <span className="soon-tag">soon</span>
            </span>
          ) : (
            <Link
              key={n.href}
              href={n.href}
              className={`nav-item ${active(n.href) ? "active" : ""}`}
            >
              {n.label}
            </Link>
          )
        )}
      </nav>
      <div className="sidebar-foot">v2 · mission runtime</div>
    </aside>
  );
}
