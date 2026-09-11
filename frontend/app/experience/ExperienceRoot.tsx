"use client";

// World 1 — the cinematic journey. HTML chapters + the WebGL canvas both read scene
// ownership from ./timeline, so exactly one beat owns the viewport. A tall spacer supplies
// the scroll distance; a single progress ref (0→1) drives everything. Reduced-motion drops
// the canvas and shows the story as static, accessible copy.

import Link from "next/link";
import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { ADJ, NODES, NODE_INDEX } from "./graph";
import { BAND, SceneId, TOTAL_VH, activeScene, local, vis } from "./timeline";
import type { DebugInfo } from "./AgentWorld";

const AgentWorld = dynamic(() => import("./AgentWorld"), { ssr: false });

const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
const smooth = (x: number) => x * x * (3 - 2 * x);

const OVERLAY_IDS: SceneId[] = [
  "hero", "t0", "researcher", "planner", "coder", "analyst",
  "team", "words", "comms", "networkReveal", "networkExplore", "payoff",
];

export default function ExperienceRoot() {
  const progress = useRef(0);
  const [reduced, setReduced] = useState(true);
  const [ready, setReady] = useState(false);
  const [debug, setDebug] = useState(false);
  const [hover, setHover] = useState<string | null>(null);
  const layers = useRef<Record<string, HTMLElement | null>>({});
  const heroRef = useRef<HTMLDivElement>(null);
  const inspector = useRef<HTMLDivElement>(null);
  const debugRef = useRef<HTMLDivElement>(null);
  const dbg = useRef<DebugInfo>({ camZ: 0, mascots: {}, active: "hero" });
  const mouse = useRef({ x: 0, y: 0 });

  const apply = () => {
    const p = progress.current;
    for (const id of OVERLAY_IDS) {
      const el = layers.current[id];
      if (!el) continue;
      const o = vis(p, BAND[id]);
      el.style.opacity = String(o);
      el.style.pointerEvents = o > 0.6 ? "auto" : "none";
      if (o > 0.5) el.classList.add("active"); else el.classList.remove("active");
    }
    if (heroRef.current) {
      const lp = local(p, BAND.hero);
      // full until 55% of the hero band, then recede in depth + fade out completely.
      const out = smooth(clamp01((lp - 0.55) / 0.45));
      const op = 1 - out;
      const el = heroRef.current;
      el.style.opacity = String(op);
      el.style.visibility = op < 0.02 ? "hidden" : "visible";
      el.style.pointerEvents = op > 0.6 ? "auto" : "none";
      // KEEP the centering translate — omitting it was parking the hero off-centre.
      el.style.transform = `translate(-50%, -50%) scale(${1 - out * 0.28}) translateY(${-out * 60}px)`;
      el.style.filter = out > 0.01 ? `blur(${out * 3}px)` : "none";
    }
    if (debug && debugRef.current) {
      const sc = activeScene(p);
      const ms = dbg.current.mascots;
      const shown = Object.keys(ms).filter((k) => ms[k] > 0.05).map((k) => `${k} ${ms[k]}`).join(", ") || "none";
      debugRef.current.textContent =
        `scroll ${p.toFixed(3)} · scene ${sc} · local ${local(p, BAND[sc]).toFixed(2)} · camZ ${dbg.current.camZ} · mascots: ${shown}`;
    }
  };

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    setDebug(new URLSearchParams(window.location.search).get("debugExperience") === "1");
    const t = setTimeout(() => setReady(true), 60);

    let lenis: any = null;
    let raf = 0;
    const onScroll = () => {
      const h = document.documentElement.scrollHeight - window.innerHeight;
      progress.current = h > 0 ? Math.min(1, Math.max(0, window.scrollY / h)) : 0;
      apply();
    };
    const onMouse = (e: MouseEvent) => {
      mouse.current = { x: e.clientX, y: e.clientY };
      if (inspector.current && inspector.current.style.opacity !== "0") {
        inspector.current.style.left = `${Math.min(e.clientX + 18, window.innerWidth - 260)}px`;
        inspector.current.style.top = `${Math.min(e.clientY + 18, window.innerHeight - 150)}px`;
      }
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("mousemove", onMouse);
    (async () => {
      if (!mq.matches) {
        const Lenis = (await import("lenis")).default;
        lenis = new Lenis({ duration: 1.15, smoothWheel: true });
        const loop = (time: number) => { lenis.raf(time); raf = requestAnimationFrame(loop); };
        raf = requestAnimationFrame(loop);
      }
      onScroll();
    })();
    return () => {
      clearTimeout(t); cancelAnimationFrame(raf); lenis?.destroy?.();
      window.removeEventListener("scroll", onScroll); window.removeEventListener("mousemove", onMouse);
    };
  }, [debug]);

  useEffect(() => {
    if (!inspector.current) return;
    inspector.current.style.opacity = hover ? "1" : "0";
    if (hover) {
      inspector.current.style.left = `${Math.min(mouse.current.x + 18, window.innerWidth - 260)}px`;
      inspector.current.style.top = `${Math.min(mouse.current.y + 18, window.innerHeight - 150)}px`;
    }
  }, [hover]);

  const node = hover ? NODES[NODE_INDEX[hover]] : null;
  const set = (id: string) => (el: HTMLElement | null) => { layers.current[id] = el; };

  return (
    <div className={`xp ${ready ? "xp-ready" : ""}`}>
      {!reduced && <div className="xp-canvas-layer" aria-hidden="true"><AgentWorld progress={progress} onHover={setHover} debug={dbg} /></div>}

      <div className="xp-top">
        <span className="xp-online"><i />AGENT_01 ONLINE</span>
        <Link href="/os" className="xp-enter-mini">Enter the OS →</Link>
      </div>

      <div className="xp-stage">
        {/* HERO — clean, nothing else in the viewport */}
        <div className="xp-layer" ref={heroRef} style={{ opacity: 1 }}>
          <h1 className="xp-headline"><span>BUILD AGENTS.</span><span>GIVE THEM TOOLS.</span><span>LET THEM WORK.</span></h1>
          <p className="xp-sub">Your AI workforce starts here.</p>
          <div className="xp-cta">
            <Link href="/agents/new" className="xp-btn primary">Create your first agent</Link>
            <Link href="/os" className="xp-btn ghost">Enter the OS</Link>
          </div>
          <div className="xp-scrollhint">scroll to descend ↓</div>
        </div>

        {/* transition — follow the signal */}
        <div className="xp-layer" ref={set("t0")} style={{ opacity: 0 }}>
          <span className="xp-signal-dot" /><h2 className="xp-big">FOLLOW THE SIGNAL</h2>
        </div>

        {/* solo agent introductions */}
        <Intro setter={set("researcher")} side="left" name="Researcher"
          line={"I disappear into the\nrabbit hole so you\ndon’t have to."} words={["WEB", "PAPERS", "SOURCES"]} />
        <Intro setter={set("planner")} side="right" name="Planner"
          line={"I turn one messy goal\ninto a plan everyone\ncan execute."} words={["GOAL", "TASKS", "SCHEDULE"]} />
        <Intro setter={set("coder")} side="left" name="Coder"
          line={"I write it. I run it.\nI break it. I fix it."} words={["RUN", "ERROR", "RETRY", "PASS ✓"]} />
        <Intro setter={set("analyst")} side="center" name="Analyst"
          line={"Give me messy data.\nI’ll find the story."} words={["NOISE", "SIGNAL", "INSIGHT"]} />

        {/* team reunion */}
        <div className="xp-layer" ref={set("team")} style={{ opacity: 0 }}>
          <span className="xp-kicker">You&apos;ve met the team</span>
          <h2 className="xp-big">FOUR AGENTS.<br />ONE SYSTEM.</h2>
        </div>

        {/* floating work words */}
        <div className="xp-layer" ref={set("words")} style={{ opacity: 0 }}>
          <div className="xp-words">
            {["PLAN", "SEARCH", "REMEMBER", "CODE", "ANALYZE", "VERIFY", "COLLABORATE", "DELIVER"].map((w, i) => (
              <span key={w} className={`xp-word w${i}`}>{w}</span>
            ))}
          </div>
        </div>

        {/* communication */}
        <div className="xp-layer" ref={set("comms")} style={{ opacity: 0 }}>
          <h2 className="xp-big">THEY DON&apos;T WORK ALONE.</h2>
          <h2 className="xp-big xp-accent">THEY THINK TOGETHER.</h2>
        </div>

        {/* network reveal */}
        <div className="xp-layer" ref={set("networkReveal")} style={{ opacity: 0 }}>
          <span className="xp-kicker">The system behind them</span>
          <h2 className="xp-big">AN ENTIRE<br />AGENT NETWORK.</h2>
        </div>

        {/* networkExplore: no overlay — the interaction is discoverable by moving the cursor */}

        {/* payoff */}
        <div className="xp-layer" ref={set("payoff")} style={{ opacity: 0 }}>
          <h2 className="xp-big">BEHIND EVERY CUTE AGENT<br />IS A SERIOUS RUNTIME.</h2>
          <p className="xp-sub">Planning · tools · memory · governance · recovery · evaluation.</p>
          <div className="xp-cta">
            <Link href="/agents/new" className="xp-btn primary">Build your own agent</Link>
            <Link href="/os" className="xp-btn ghost">Enter mission control</Link>
          </div>
        </div>
      </div>

      <div className="xp-inspector" ref={inspector} style={{ opacity: 0 }} aria-hidden="true">
        {node && (
          <>
            <div className="xp-insp-kind" style={{ color: kindColor(node.kind) }}>{node.kind}</div>
            <div className="xp-insp-name">{node.label}</div>
            <div className="xp-insp-desc">{node.desc}</div>
            {ADJ[node.id]?.length > 0 && (
              <div className="xp-insp-conn">→ {ADJ[node.id].slice(0, 4).map((c) => NODES[NODE_INDEX[c]].label).join(" · ")}</div>
            )}
          </>
        )}
      </div>

      {debug && <div className="xp-debug" ref={debugRef} />}

      <div className="xp-spacer" style={{ height: reduced ? "auto" : `${TOTAL_VH}vh` }}>
        {reduced && <ReducedFallback />}
      </div>
    </div>
  );
}

function kindColor(kind: string) {
  return { agent: "#6EA8FF", system: "#C9D3E0", memory: "#8B7DF6", tool: "#4ADE80", data: "#F5C542" }[kind] || "#8A9099";
}

function Intro({ setter, side, name, line, words }: { setter: (el: HTMLElement | null) => void; side: "left" | "center" | "right"; name: string; line: string; words: string[] }) {
  const arrows: Record<string, string> = {
    left: "M20,16 C90,8 128,60 150,104",
    center: "M120,8 C120,60 120,86 120,132",
    right: "M220,16 C150,8 112,60 90,104",
  };
  return (
    <div className={`xp-layer xp-intro xp-intro-${side}`} ref={setter} style={{ opacity: 0 }}>
      <div className="xp-annot">
        <p className="xp-dialogue">{line.split("\n").map((l, i) => <span key={i}>{l}<br /></span>)}</p>
        <svg className="xp-arrow" viewBox="0 0 240 140" fill="none">
          <path d={arrows[side]} stroke="#cdd6e5" strokeWidth="2" strokeLinecap="round" markerEnd="url(#xp-ah)" pathLength={1} />
          <defs><marker id="xp-ah" markerWidth="9" markerHeight="9" refX="5" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 Z" fill="#cdd6e5" /></marker></defs>
        </svg>
        <span className="xp-annot-name">{name}</span>
        <div className="xp-microwords">{words.map((w) => <span key={w}>{w}</span>)}</div>
      </div>
    </div>
  );
}

function ReducedFallback() {
  return (
    <div className="xp-reduced">
      <h1 className="xp-headline"><span>BUILD AGENTS.</span><span>GIVE THEM TOOLS.</span><span>LET THEM WORK.</span></h1>
      <p className="xp-sub">Your AI workforce starts here.</p>
      <div className="xp-cta"><Link href="/agents/new" className="xp-btn primary">Create your first agent</Link><Link href="/os" className="xp-btn ghost">Enter the OS</Link></div>
      <h2 className="xp-big" style={{ marginTop: 60 }}>Four agents. One system.</h2>
      <p className="xp-sub">A planner, researcher, coder and analyst plan, use tools, remember, collaborate, check their work and bring back real artifacts — governed by policy and human approval.</p>
      <h2 className="xp-big" style={{ marginTop: 40 }}>Behind every cute agent is a serious runtime.</h2>
      <p className="xp-sub">Planning · tools · memory · governance · recovery · evaluation.</p>
    </div>
  );
}
