"use client";

// World 1 — the cinematic public landing. One persistent 3D canvas (AgentWorld) sits
// behind semantic HTML scenes. Lenis drives smooth scroll; a single normalized progress
// ref (0→1) feeds the canvas camera. All copy is real HTML (accessible + SEO), so with
// prefers-reduced-motion we simply drop the canvas and animations and keep the content.

import Link from "next/link";
import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import { CREW, HERO_LABELS } from "./scenes";

const AgentWorld = dynamic(() => import("./AgentWorld"), { ssr: false });

export default function ExperienceRoot() {
  const progress = useRef(0);
  const [reduced, setReduced] = useState(true); // assume reduced until we confirm otherwise (SSR-safe)
  const [enter, setEnter] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const isReduced = mq.matches;
    setReduced(isReduced);
    // boot reveal
    const t = setTimeout(() => setEnter(true), 60);

    let lenis: { raf: (t: number) => void; destroy: () => void; on: (e: string, cb: (a: { progress: number }) => void) => void } | null = null;
    let raf = 0;
    let cleanupObs: (() => void) | undefined;

    (async () => {
      if (!isReduced) {
        const Lenis = (await import("lenis")).default;
        lenis = new Lenis({ duration: 1.1, smoothWheel: true }) as unknown as typeof lenis;
        const loop = (time: number) => { lenis?.raf(time); raf = requestAnimationFrame(loop); };
        raf = requestAnimationFrame(loop);
      }
      const onScroll = () => {
        const h = document.documentElement.scrollHeight - window.innerHeight;
        progress.current = h > 0 ? Math.min(1, Math.max(0, window.scrollY / h)) : 0;
      };
      window.addEventListener("scroll", onScroll, { passive: true });
      onScroll();

      // reveal scenes on enter
      const obs = new IntersectionObserver(
        (entries) => entries.forEach((e) => e.isIntersecting && e.target.classList.add("in")),
        { threshold: 0.25 },
      );
      document.querySelectorAll(".xp-scene").forEach((el) => obs.observe(el));
      cleanupObs = () => { window.removeEventListener("scroll", onScroll); obs.disconnect(); };
    })();

    return () => { clearTimeout(t); cancelAnimationFrame(raf); lenis?.destroy?.(); cleanupObs?.(); };
  }, []);

  return (
    <div className={`xp ${enter ? "xp-ready" : ""}`}>
      {!reduced && <div className="xp-canvas-layer" aria-hidden="true"><AgentWorld progress={progress} /></div>}

      {/* top status chip */}
      <div className="xp-top">
        <span className="xp-online"><i />AGENT_01 ONLINE</span>
        <Link href="/os" className="xp-enter-mini">Enter the OS →</Link>
      </div>

      {/* SCENE 01 — boot / hero */}
      <section className="xp-scene xp-hero in">
        <div className="xp-labels" aria-hidden="true">
          {HERO_LABELS.map((l, i) => <span key={l} className={`xp-label l${i}`}>{l}</span>)}
        </div>
        <h1 className="xp-headline">
          <span>BUILD AGENTS.</span>
          <span>GIVE THEM TOOLS.</span>
          <span>LET THEM WORK.</span>
        </h1>
        <p className="xp-sub">Your AI workforce starts here.</p>
        <div className="xp-cta">
          <Link href="/agents/new" className="xp-btn primary">Create your first agent</Link>
          <Link href="/os" className="xp-btn ghost">Enter the OS</Link>
        </div>
        <div className="xp-scrollhint" aria-hidden="true">scroll to meet them ↓</div>
      </section>

      {/* SCENE 02 — meet the agents */}
      <section className="xp-scene xp-crew">
        <div className="xp-crew-intro">
          <span className="xp-kicker">Meet the crew</span>
          <h2>They&apos;re not mascots. They&apos;re agents.</h2>
          <p>Each one has a speciality, its own tools and its own memory.</p>
        </div>
        <div className="xp-crew-grid">
          {CREW.map((c, i) => (
            <Link key={c.id} href="/agents/new" className={`xp-agent a${i}`} style={{ ["--accent" as string]: c.accent }}>
              <span className="xp-agent-glow" aria-hidden="true" />
              <img src={c.img} alt={`${c.name} agent`} className="xp-agent-img" loading="lazy" />
              <span className="xp-agent-tag">{c.role}</span>
              <span className="xp-agent-name">{c.name}</span>
              <span className="xp-agent-line">“{c.line}”</span>
            </Link>
          ))}
        </div>
      </section>

      {/* closing bridge into the OS */}
      <section className="xp-scene xp-bridge">
        <h2 className="xp-bridge-title">Behind every cute agent<br />is a serious runtime.</h2>
        <p className="xp-sub">Planning · tools · memory · governance · recovery · evaluation.</p>
        <div className="xp-cta">
          <Link href="/agents/new" className="xp-btn primary">Build your own agent</Link>
          <Link href="/os" className="xp-btn ghost">Enter mission control</Link>
        </div>
      </section>
    </div>
  );
}
