"use client";

import { useEffect, useMemo, useState } from "react";
import "../tools.css";
import Icon from "../components/Icon";
import ToolMetrics from "../components/tools/ToolMetrics";
import ToolGrid from "../components/tools/ToolGrid";
import ToolDetailDrawer from "../components/tools/ToolDetailDrawer";
import { ToolView, Category, CATEGORIES, fetchTools, catalogMetrics } from "../lib/toolsApi";

export default function ToolsPage() {
  const [tools, setTools] = useState<ToolView[]>([]);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<Category | "all">("all");
  const [sort, setSort] = useState<"category" | "name">("category");
  const [openId, setOpenId] = useState<string | null>(null);

  useEffect(() => { fetchTools().then(setTools); }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return tools.filter((t) => {
      if (category !== "all" && t.category !== category) return false;
      if (!q) return true;
      const hay = [t.displayName, t.id, t.description, t.category, ...t.safety, ...t.agents].join(" ").toLowerCase();
      return hay.includes(q);
    });
  }, [tools, query, category]);

  const groups = useMemo(() => {
    if (sort === "name") {
      return [{ title: "", tools: [...filtered].sort((a, b) => a.displayName.localeCompare(b.displayName)) }];
    }
    return CATEGORIES.map((c) => ({ title: c, tools: filtered.filter((t) => t.category === c) }));
  }, [filtered, sort]);

  const open = tools.find((t) => t.id === openId) || null;
  const m = catalogMetrics(tools);

  return (
    <div className="tools">
      <div className="wrap">
        <div className="head">
          <div>
            <h1 className="h1">Tools</h1>
            <p className="h-sub">Capabilities available to your agents.</p>
          </div>
          <div className="search">
            <Icon name="search" size={15} />
            <input placeholder="Search tools..." value={query} onChange={(e) => setQuery(e.target.value)} />
          </div>
        </div>

        <ToolMetrics m={m} />

        <div className="filters">
          <button className={`chip ${category === "all" ? "active" : ""}`} onClick={() => setCategory("all")}>All</button>
          {CATEGORIES.map((c) => (
            <button key={c} className={`chip ${category === c ? "active" : ""}`} onClick={() => setCategory(c)}>{c}</button>
          ))}
          <select className="sortsel" value={sort} onChange={(e) => setSort(e.target.value as "category" | "name")} aria-label="Sort">
            <option value="category">Group by category</option>
            <option value="name">Sort by name</option>
          </select>
        </div>

        <ToolGrid groups={groups} onOpen={(t) => setOpenId(t.id)} />
      </div>

      {open && <ToolDetailDrawer tool={open} onClose={() => setOpenId(null)} />}
    </div>
  );
}
