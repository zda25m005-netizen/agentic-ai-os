"use client";

// Character showcase (Phase 2). Renders every character in the registry across a few
// representative states so the character system can be reviewed at a glance. This is a
// presentation gallery — it does not fabricate any agent activity.

import { useState } from "react";
import AgentCharacter from "../components/AgentCharacter";
import { AGENT_STATES, CHARACTERS, STATE_LABEL, type AgentState } from "../lib/characters";

const PREVIEW_STATES: AgentState[] = ["idle", "thinking", "working", "completed"];

export default function CharactersPage() {
  const [state, setState] = useState<AgentState>("idle");

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Characters</h1>
          <p className="page-sub">
            {CHARACTERS.length} reusable agent characters. Each is a presentation identity —
            the intelligence comes from the mission runtime, memory and tools.
          </p>
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {AGENT_STATES.map((s) => (
            <button
              key={s}
              className="agent-btn"
              onClick={() => setState(s)}
              style={{
                padding: "6px 10px",
                fontSize: 12,
                background: s === state ? "var(--accent)" : undefined,
                color: s === state ? "#fff" : undefined,
              }}
            >
              {STATE_LABEL[s]}
            </button>
          ))}
        </div>
      </div>

      <div className="ch-grid">
        {CHARACTERS.map((c) => (
          <div key={c.id} className="ch-card">
            <AgentCharacter character={c.id} state={state} size={84} />
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span className="ch-accent" style={{ background: c.accent }} />
              <span className="ch-name">{c.name}</span>
            </div>
            <div className="ch-desc">{c.description}</div>
            <div className="ch-states">
              {PREVIEW_STATES.map((s) => (
                <div key={s} className="ch-state">
                  <AgentCharacter character={c.id} state={s} size={40} />
                  <span>{STATE_LABEL[s]}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
