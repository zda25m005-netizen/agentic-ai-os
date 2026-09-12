"use client";

// World 1 — the cinematic journey. The hero + "follow the signal" beats are DOM chapters
// with their original timing. Everything from the first agent introduction onward is a
// single continuous 3D world rendered on the persistent canvas (see ./SpatialWorld); the
// only DOM there is the neural hover inspector, the governance approval moment, and the
// final CTA. A single scroll progress ref (0→1) drives everything. Reduced-motion drops the
// canvas and shows the story as static, accessible copy.

import Link from "next/link";
import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { ADJ, NODES, NODE_INDEX } from "./graph";
import { BAND, TOTAL_VH, activeScene, local, vis } from "./timeline";
import { BOUNDARY, focusedAgent, regionAt, toWorld, worldActivation } from "./world";
import type { DebugInfo } from "./AgentWorld";

const AgentWorld = dynamic(() => import("./AgentWorld"), { ssr: false });

const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
const smooth = (x: number) => x * x * (3 - 2 * x);
// a windowed 0→1 bump: fade in over `fade`, hold, fade out over `fade`.
const bump = (w: number, s: number, e: number, fade = 0.25) => {
  if (w <= s || w >= e) return 0;
  const t = (w - s) / (e - s);
  return Math.min(smooth(clamp01(t / fade)), smooth(clamp01((1 - t) / fade)));
};

export default function ExperienceRoot() {
  const progress = useRef(0);
  const [reduced, setReduced] = useState(true);
  const [ready, setReady] = useState(false);
  const [debug, setDebug] = useState(false);
  const [debugComp, setDebugComp] = useState(false);
  const [hover, setHover] = useState<string | null>(null);
  const introRef = useRef<HTMLDivElement>(null);
  const heroRef = useRef<HTMLDivElement>(null);
  const t0Ref = useRef<HTMLDivElement>(null);
  const ctaRef = useRef<HTMLDivElement>(null);
  const approvalRef = useRef<HTMLDivElement>(null);
  const inspector = useRef<HTMLDivElement>(null);
  const debugRef = useRef<HTMLDivElement>(null);
  const compRef = useRef<HTMLDivElement>(null);
  const atmosRef = useRef<HTMLDivElement>(null);
  const hudRef = useRef<HTMLDivElement>(null);
  const hudIdxRef = useRef<HTMLSpanElement>(null);
  const hudRoleRef = useRef<HTMLSpanElement>(null);
  const dbg = useRef<DebugInfo>({ camZ: 0, mascots: {}, active: "hero" });
  const mouse = useRef({ x: 0, y: 0 });

  const apply = () => {
    const p = progress.current;
    const w = toWorld(p);

    // intro — the floating particle cloud moment, before the hero
    if (introRef.current) {
      const lp = local(p, BAND.intro);
      const op = 1 - smooth(clamp01((lp - 0.55) / 0.45));
      const el = introRef.current;
      el.style.opacity = String(op);
      el.style.visibility = op < 0.02 ? "hidden" : "visible";
      el.style.transform = `translateY(${-(1 - op) * 40}px)`;
    }
    // hero — fades in as the intro clears, then full until 55% of its band (unchanged after that)
    if (heroRef.current) {
      const lp = local(p, BAND.hero);
      const out = smooth(clamp01((lp - 0.55) / 0.45));
      const op = smooth(clamp01(lp / 0.18)) * (1 - out);
      const el = heroRef.current;
      el.style.opacity = String(op);
      el.style.visibility = op < 0.02 ? "hidden" : "visible";
      el.style.pointerEvents = op > 0.6 ? "auto" : "none";
      el.style.transform = `translate(-50%, -50%) scale(${1 - out * 0.28}) translateY(${-out * 60}px)`;
      el.style.filter = out > 0.01 ? `blur(${out * 3}px)` : "none";
    }
    // "follow the signal" connector (unchanged band)
    if (t0Ref.current) {
      const o = vis(p, BAND.t0);
      t0Ref.current.style.opacity = String(o);
      t0Ref.current.classList.toggle("active", o > 0.5);
    }
    // governance approval — the one place normal UI is appropriate
    if (approvalRef.current) {
      const o = bump(w, 0.948, 0.969, 0.3);
      approvalRef.current.style.opacity = String(o);
      approvalRef.current.style.pointerEvents = o > 0.6 ? "auto" : "none";
    }
    // atmosphere vignette + "+" registration grid — appear only once the hero has left
    if (atmosRef.current) atmosRef.current.style.opacity = String(worldActivation(p));
    // technical HUD — index + role of whichever agent owns the frame
    if (hudRef.current) {
      const fa = focusedAgent(w);
      hudRef.current.style.opacity = String(fa ? fa.f * worldActivation(p) : 0);
      if (fa) {
        if (hudIdxRef.current) hudIdxRef.current.textContent = `[[  ${fa.idx}  ]]`;
        if (hudRoleRef.current) hudRoleRef.current.textContent = fa.role;
      }
    }
    // final CTA — only after all the spatial storytelling
    if (ctaRef.current) {
      const o = smooth(clamp01((w - 0.986) / 0.014));
      ctaRef.current.style.opacity = String(o);
      ctaRef.current.style.pointerEvents = o > 0.6 ? "auto" : "none";
    }

    if (debug && debugRef.current) {
      const sc = activeScene(p);
      debugRef.current.textContent =
        `scroll ${p.toFixed(3)} · world ${w.toFixed(3)} · scene ${sc} · camZ ${dbg.current.camZ}`;
    }
    if (debugComp && compRef.current) {
      compRef.current.textContent =
        `region: ${p < BOUNDARY ? "hero / pre-agent" : regionAt(w)}  ·  world ${w.toFixed(3)}  ·  camZ ${dbg.current.camZ}`;
    }
  };

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const qs = new URLSearchParams(window.location.search);
    setDebug(qs.get("debugExperience") === "1");
    setDebugComp(qs.get("debugComposition") === "1");
    const t = setTimeout(() => setReady(true), 60);

    let lenis: { raf: (t: number) => void; destroy?: () => void } | null = null;
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
        const loop = (time: number) => { lenis!.raf(time); raf = requestAnimationFrame(loop); };
        raf = requestAnimationFrame(loop);
      }
      onScroll();
    })();
    return () => {
      clearTimeout(t); cancelAnimationFrame(raf); lenis?.destroy?.();
      window.removeEventListener("scroll", onScroll); window.removeEventListener("mousemove", onMouse);
    };
  }, [debug, debugComp]);

  useEffect(() => {
    if (!inspector.current) return;
    inspector.current.style.opacity = hover ? "1" : "0";
    if (hover) {
      inspector.current.style.left = `${Math.min(mouse.current.x + 18, window.innerWidth - 260)}px`;
      inspector.current.style.top = `${Math.min(mouse.current.y + 18, window.innerHeight - 150)}px`;
    }
  }, [hover]);

  const node = hover ? NODES[NODE_INDEX[hover]] : null;

  return (
    <div className={`xp ${ready ? "xp-ready" : ""}`}>
      {!reduced && <div className="xp-canvas-layer" aria-hidden="true"><AgentWorld progress={progress} onHover={setHover} debug={dbg} /></div>}

      {/* full-bleed atmosphere: cinematic vignette + faint "+" registration grid (post-hero) */}
      {!reduced && (
        <div className="xp-atmos" ref={atmosRef} style={{ opacity: 0 }} aria-hidden="true">
          <div className="xp-atmos-vignette" />
          <div className="xp-plusgrid">
            {[[10, 56], [30, 56], [50, 56], [70, 56], [90, 56], [6, 12], [94, 12], [6, 90], [94, 90]].map(([x, y], i) => (
              <span key={i} style={{ left: `${x}%`, top: `${y}%` }}>+</span>
            ))}
          </div>
        </div>
      )}

      {/* technical HUD framing — index, tick rulers, role of the focused agent */}
      {!reduced && (
        <div className="xp-hud" ref={hudRef} style={{ opacity: 0 }} aria-hidden="true">
          <span className="xp-hud-idx" ref={hudIdxRef}>[[  001  ]]</span>
          <div className="xp-hud-ticks xp-hud-ticks-top" />
          <div className="xp-hud-ticks xp-hud-ticks-bottom" />
          <div className="xp-hud-role"><i /><span ref={hudRoleRef} /></div>
        </div>
      )}

      <div className="xp-top">
        <span className="xp-online"><i />AGENT_01 ONLINE</span>
        <Link href="/os" className="xp-enter-mini">Enter the OS →</Link>
      </div>

      <div className="xp-stage">
        {/* INTRO — floating particle cloud moment, before the hero */}
        <div className="xp-introlayer" ref={introRef} style={{ opacity: 1 }}>
          <span className="xp-kicker-intro">THEY THINK · THEY ACT · THEY REPORT BACK</span>
          <h1 className="xp-wordmark">AUTONOMY</h1>
          <span className="xp-scrollexplore">SCROLL TO EXPLORE</span>
        </div>

        {/* HERO — clean, nothing else in the viewport (untouched) */}
        <div className="xp-layer" ref={heroRef} style={{ opacity: 1 }}>
          <h1 className="xp-headline"><span>BUILD AGENTS.</span><span>GIVE THEM TOOLS.</span><span>LET THEM WORK.</span></h1>
          <p className="xp-sub">Your AI workforce starts here.</p>
          <div className="xp-cta">
            <Link href="/agents/new" className="xp-btn primary">Create your first agent</Link>
            <Link href="/os" className="xp-btn ghost">Enter the OS</Link>
          </div>
          <div className="xp-scrollhint">scroll to descend ↓</div>
        </div>

        {/* transition — follow the signal (untouched) */}
        <div className="xp-layer" ref={t0Ref} style={{ opacity: 0 }}>
          <span className="xp-signal-dot" /><h2 className="xp-big">FOLLOW THE SIGNAL</h2>
        </div>

        {/* everything from here is the 3D world — the only DOM is below */}

        {/* governance approval moment */}
        <div className="xp-layer xp-approval" ref={approvalRef} style={{ opacity: 0 }}>
          <span className="xp-approval-tag">APPROVAL REQUIRED</span>
          <p className="xp-approval-body">An agent wants to run a real action. You stay in control.</p>
          <div className="xp-approval-actions">
            <span className="xp-btn primary">Allow</span>
            <span className="xp-btn ghost">Deny</span>
          </div>
        </div>

        {/* final CTA — after the pull-back, kept low + clear of the monumental type */}
        <div className="xp-layer xp-cta-final" ref={ctaRef} style={{ opacity: 0 }}>
          <div className="xp-cta">
            <Link href="/agents/new" className="xp-btn primary">Build your own agent</Link>
            <Link href="/os" className="xp-btn ghost">Enter mission control</Link>
          </div>
        </div>
      </div>

      {debugComp && (
        <div className="xp-compdbg" aria-hidden="true">
          <div className="xp-compdbg-safe" />
          <div className="xp-compdbg-hud" ref={compRef} />
        </div>
      )}

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

      <span className="xp-boundary-marker" data-boundary={BOUNDARY.toFixed(4)} hidden />
    </div>
  );
}

function kindColor(kind: string) {
  return { agent: "#6EA8FF", system: "#C9D3E0", memory: "#8B7DF6", tool: "#4ADE80", data: "#F5C542" }[kind] || "#8A9099";
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
