"use client";

import { useEffect, useMemo, useState } from "react";
import "../agents.css";
import Icon from "../components/Icon";
import AgentMetrics from "../components/agents/AgentMetrics";
import AgentGrid from "../components/agents/AgentGrid";
import AgentLoop from "../components/agents/AgentLoop";
import AgentDetailDrawer from "../components/agents/AgentDetailDrawer";
import { AGENTS, AgentView, RoleGroup, ROLE_GROUPS } from "../lib/agentsData";
import { api } from "../lib/api";

export default function AgentsPage() {
  const [query, setQuery] = useState("");
  const [role, setRole] = useState<RoleGroup | "all">("all");
  const [openId, setOpenId] = useState<string | null>(null);
  const [missions, setMissions] = useState<number | null>(null);

  useEffect(() => { api.listMissions().then((m) => setMissions(m.length)).catch(() => setMissions(null)); }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return AGENTS.filter((a) => {
      if (role !== "all" && a.role !== role) return false;
      if (!q) return true;
      return [a.name, a.role, a.description, ...a.responsibilities, ...a.tools].join(" ").toLowerCase().includes(q);
    });
  }, [query, role]);

  const open = AGENTS.find((a) => a.id === openId) || null;

  return (
    <div className="ag">
      <div className="wrap">
        <div className="head">
          <div>
            <h1 className="h1">Agents</h1>
            <p className="h-sub">Role-specialized agents that plan, execute, evaluate, and complete missions.</p>
          </div>
          <div className="search">
            <Icon name="search" size={15} />
            <input placeholder="Search agents..." value={query} onChange={(e) => setQuery(e.target.value)} />
          </div>
        </div>

        <AgentMetrics missions={missions} />

        <div className="filters">
          <button className={`chip ${role === "all" ? "active" : ""}`} onClick={() => setRole("all")}>All</button>
          {ROLE_GROUPS.map((r) => (
            <button key={r} className={`chip ${role === r ? "active" : ""}`} onClick={() => setRole(r)}>{r}</button>
          ))}
        </div>

        <div className="sec-h">Agents</div>
        <AgentGrid agents={filtered} onOpen={(a: AgentView) => setOpenId(a.id)} />

        <div className="sec-h">Agent Loop</div>
        <AgentLoop />
      </div>

      {open && <AgentDetailDrawer agent={open} onClose={() => setOpenId(null)} />}
    </div>
  );
}
