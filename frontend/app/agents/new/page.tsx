"use client";

// Create Agent flow (Phase 5). Three modes:
//   A. Describe it   — natural language -> generated spec (real /agents/spec) -> edit -> character -> create
//   B. From template — pick a built-in template
//   C. From scratch  — advanced field editor
// Everything writes a real, persisted, owner-scoped agent via /agents. No fake state.

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import AgentCharacter from "../../components/AgentCharacter";
import { CHARACTERS } from "../../lib/characters";
import {
  type AgentSpec,
  type TemplateDTO,
  createAgent,
  generateSpec,
  listAgents,
  listTemplates,
} from "../../lib/agentsApi";

type Mode = "describe" | "template" | "scratch";
type Step = "mode" | "describe" | "spec" | "character";

const EXAMPLES = [
  "Find AI/ML jobs for me every morning, dedupe them, compare with my resume and send me the best matches.",
  "Find funded PhD positions in Norway in machine learning and rank them against my profile.",
  "Summarize new arXiv papers on retrieval-augmented generation each week.",
];

export default function CreateAgentPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("describe");
  const [step, setStep] = useState<Step>("mode");
  const [desc, setDesc] = useState("");
  const [spec, setSpec] = useState<AgentSpec | null>(null);
  const [templates, setTemplates] = useState<TemplateDTO[]>([]);
  const [usedChars, setUsedChars] = useState<string[]>([]);
  const [chosenChar, setChosenChar] = useState<string>("nova");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    listTemplates().then(setTemplates).catch(() => setErr("Can't reach the agent service (start the API on :8000)."));
    listAgents().then((a) => setUsedChars(a.map((x) => x.character_id))).catch(() => {});
    // Prefill from Home's ask bar: /agents/new?desc=...
    const q = new URLSearchParams(window.location.search).get("desc");
    if (q) { setDesc(q); setMode("describe"); setStep("describe"); }
  }, []);

  const freeChar = useMemo(() => {
    const used = new Set(usedChars);
    return CHARACTERS.find((c) => !used.has(c.id))?.id || "nova";
  }, [usedChars]);

  async function onGenerate() {
    if (!desc.trim()) return;
    setBusy(true); setErr(null);
    try {
      const s = await generateSpec(desc.trim());
      setSpec(s);
      setChosenChar(s.suggested_character_id || freeChar);
      setStep("spec");
    } catch {
      setErr("Couldn't generate a spec. Is the API running on :8000?");
    } finally { setBusy(false); }
  }

  async function onCreate() {
    if (!spec) return;
    setBusy(true); setErr(null);
    try {
      await createAgent({
        name: spec.name,
        description: spec.description,
        purpose: spec.purpose,
        instructions: spec.instructions,
        tools: spec.tools,
        memory_config: spec.memory_config,
        schedule: spec.schedule,
        approval_policy: spec.approval_policy,
        personality: spec.personality,
        template_id: spec.template_id,
        character_id: chosenChar,
      });
      router.push("/agents");
    } catch {
      setErr("Couldn't create the agent. Is the API running on :8000?");
    } finally { setBusy(false); }
  }

  async function onCreateTemplate(t: TemplateDTO) {
    setBusy(true); setErr(null);
    try { await createAgent({ template_id: t.id }); router.push("/agents"); }
    catch { setErr("Couldn't create the agent."); }
    finally { setBusy(false); }
  }

  const setField = (k: keyof AgentSpec, v: unknown) => setSpec((s) => (s ? { ...s, [k]: v } as AgentSpec : s));

  return (
    <div className="page" style={{ maxWidth: 820 }}>
      <div className="page-head">
        <div>
          <h1 className="page-title">Create agent</h1>
          <p className="page-sub">Tell it what to do, pick a character, and it joins your team.</p>
        </div>
      </div>
      {err && <div className="ag-note">{err}</div>}

      {/* STEP: choose mode */}
      {step === "mode" && (
        <div className="team-grid">
          <button className="team-card mode-card" onClick={() => { setMode("describe"); setStep("describe"); }}>
            <AgentCharacter character="nova" state="thinking" size={64} />
            <div className="team-name">Describe it</div>
            <div className="team-purpose">Say what you want in plain language.</div>
          </button>
          <button className="team-card mode-card" onClick={() => { setMode("template"); setStep("mode"); }}>
            <AgentCharacter character="peter" state="idle" size={64} />
            <div className="team-name">Start from template</div>
            <div className="team-purpose">Job search, research, PhD, and more.</div>
          </button>
          <button className="team-card mode-card" onClick={() => { setMode("scratch"); setStep("spec"); setSpec(blankSpec()); }}>
            <AgentCharacter character="atlas" state="planning" size={64} />
            <div className="team-name">Build from scratch</div>
            <div className="team-purpose">Full control over every field.</div>
          </button>
        </div>
      )}

      {/* Template picker (mode B) */}
      {step === "mode" && mode === "template" && (
        <>
          <div className="sec-title" style={{ margin: "24px 0 12px" }}>Choose a template</div>
          <div className="team-grid">
            {templates.map((t) => (
              <div key={t.id} className="team-card">
                <AgentCharacter character={t.character_id} state="idle" size={56} />
                <div className="team-name">{t.name}</div>
                <div className="team-purpose">{t.description}</div>
                <button className="agent-btn" disabled={busy} onClick={() => onCreateTemplate(t)}>Create agent</button>
              </div>
            ))}
          </div>
        </>
      )}

      {/* STEP: describe */}
      {step === "describe" && (
        <div className="create-panel">
          <label className="create-label">Tell me what you want your agent to do.</label>
          <textarea className="create-textarea" rows={5} value={desc} placeholder="e.g. Find AI/ML jobs every morning and send me the best matches…"
            onChange={(e) => setDesc(e.target.value)} />
          <div className="create-examples">
            {EXAMPLES.map((ex) => (
              <button key={ex} className="chip" onClick={() => setDesc(ex)}>{ex.slice(0, 42)}…</button>
            ))}
          </div>
          <div className="create-actions">
            <button className="icon-btn" onClick={() => setStep("mode")}>Back</button>
            <button className="agent-btn" disabled={busy || !desc.trim()} onClick={onGenerate}>
              {busy ? "Generating…" : "Generate agent"}
            </button>
          </div>
        </div>
      )}

      {/* STEP: spec review/edit */}
      {step === "spec" && spec && (
        <div className="create-panel">
          <div className="sec-title" style={{ marginBottom: 12 }}>Your new agent</div>
          <SpecField label="Name" value={spec.name} onChange={(v) => setField("name", v)} />
          <SpecField label="Purpose" value={spec.purpose} onChange={(v) => setField("purpose", v)} />
          <SpecArea label="Instructions" value={spec.instructions} onChange={(v) => setField("instructions", v)} />
          <SpecField label="Tools" value={spec.tools.join(", ")} onChange={(v) => setField("tools", v.split(",").map((x) => x.trim()).filter(Boolean))} />
          <div className="spec-row"><span className="spec-k">Schedule</span><span className="spec-v">{describeSchedule(spec.schedule)}</span></div>
          <div className="spec-row"><span className="spec-k">Approval</span><span className="spec-v">{spec.approval_policy?.require_approval ? "Required before actions" : "Not required"}</span></div>
          <div className="spec-row"><span className="spec-k">Personality</span><span className="spec-v">{spec.personality}</span></div>
          <div className="create-actions">
            <button className="icon-btn" onClick={() => setStep(mode === "scratch" ? "mode" : "describe")}>Back</button>
            <button className="agent-btn" onClick={() => setStep("character")}>Choose character</button>
          </div>
        </div>
      )}

      {/* STEP: choose character */}
      {step === "character" && spec && (
        <div className="create-panel">
          <div className="sec-title" style={{ marginBottom: 4 }}>Choose your agent</div>
          <p className="page-sub" style={{ marginBottom: 14 }}>Meet {CHARACTERS.find((c) => c.id === chosenChar)?.name} — {spec.name} will be your {spec.personality.toLowerCase()} assistant.</p>
          <div className="char-picker">
            {CHARACTERS.map((c) => (
              <button key={c.id} className={`char-opt ${c.id === chosenChar ? "sel" : ""}`} onClick={() => setChosenChar(c.id)} title={c.name}>
                <AgentCharacter character={c.id} state={c.id === chosenChar ? "working" : "idle"} size={56} />
                <span>{c.name}</span>
              </button>
            ))}
          </div>
          <div className="create-actions">
            <button className="icon-btn" onClick={() => setStep("spec")}>Back</button>
            <button className="agent-btn" disabled={busy} onClick={onCreate}>{busy ? "Creating…" : `Create ${spec.name}`}</button>
          </div>
        </div>
      )}
    </div>
  );
}

function blankSpec(): AgentSpec {
  return {
    name: "New Agent", description: "", purpose: "", instructions: "", tools: [],
    memory_config: {}, schedule: {}, approval_policy: {}, personality: "Friendly",
    suggested_character_id: "nova", template_id: "", generated_by: "scratch",
  };
}

function describeSchedule(s: Record<string, unknown>): string {
  if (!s || !s.cadence) return "On demand";
  if (s.cadence === "daily") return `Daily${s.time ? " at " + s.time : ""}`;
  if (s.cadence === "weekly") return `Weekly${s.day ? " on " + s.day : ""}`;
  if (s.cadence === "hourly") return "Hourly";
  return String(s.cadence);
}

function SpecField({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="spec-edit">
      <label>{label}</label>
      <input value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

function SpecArea({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div className="spec-edit">
      <label>{label}</label>
      <textarea rows={3} value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}
