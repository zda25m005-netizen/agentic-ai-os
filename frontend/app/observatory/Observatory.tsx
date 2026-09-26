"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { Component, useEffect, useState, type ReactNode, type CSSProperties } from "react";
import Icon from "../components/Icon";

const Scene = dynamic(() => import("./Scene"), { ssr: false });
export const crew = [
  { name: "Peter", title: "Your next opportunity,\na little closer.", role: "THE OPPORTUNITY SCOUT", color: "#9bbdff", image: "peter", intro: "Hey, I’m Peter.", text: "Tell me where you want to go. I’ll help you discover jobs, find the right people, and shape your next move.", skills: ["Find opportunities", "Research companies", "Draft outreach"], prompt: "Find relevant job opportunities and help me draft personalized outreach." },
  { name: "Ivy", title: "Less busywork.\nMore breathing room.", role: "THE MONEY ORGANIZER", color: "#efd294", image: "ivy", intro: "I make the numbers feel lighter.", text: "Give me the receipts, invoices, and scattered details. I’ll help turn them into an organized picture you can actually understand.", skills: ["Read invoices", "Organize receipts", "Summarize expenses"], prompt: "Organize invoices and receipts and summarize my expenses." },
  { name: "Rory", title: "Down the rabbit hole.\nBack with answers.", role: "THE CURIOUS RESEARCHER", color: "#a0dac7", image: "rory", intro: "Curiosity is kind of my thing.", text: "I follow the interesting questions. From long papers to unfamiliar topics, I help connect the dots and bring the useful bits back to you.", skills: ["Explore sources", "Compare evidence", "Summarize papers"], prompt: "Research topics, compare evidence, and summarize papers with source citations." },
  { name: "Luna", title: "Big ambitions.\nA clearer path.", role: "THE ACADEMIC EXPLORER", color: "#c4afe9", image: "luna", intro: "Let’s find where you belong.", text: "A new lab, a funded program, a question worth a few years of your life. I’ll help you explore academic opportunities that fit your interests.", skills: ["Find PhD programs", "Explore funding", "Match research interests"], prompt: "Find PhD programs and funding opportunities matching my research interests." },
];

class SceneBoundary extends Component<{ children: ReactNode; fallback: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? this.props.fallback : this.props.children; }
}

export default function Observatory() {
  const [active, setActive] = useState(-1);
  const [motion, setMotion] = useState(false);
  const [webgl, setWebgl] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setMotion(!mq.matches);
    const updateMotion = () => setMotion(!mq.matches);
    mq.addEventListener("change", updateMotion);
    const canvas = document.createElement("canvas");
    try { setWebgl(Boolean(canvas.getContext("webgl2"))); } catch { setWebgl(false); }
    const update = () => {
      let next = -1;
      document.querySelectorAll<HTMLElement>("[data-agent-section]").forEach((el) => {
        if (el.getBoundingClientRect().top < window.innerHeight * .5) next = Number(el.dataset.agentSection);
      });
      setActive(next);
    };
    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => { mq.removeEventListener("change", updateMotion); window.removeEventListener("scroll", update); window.removeEventListener("resize", update); };
  }, []);
  const current = crew[Math.max(0, Math.min(active, 3))];
  const fallback = <div className="ob-fallback"><img src={`/mascots/${active < 0 ? "team-hero" : `${current.image}-3d`}.webp`} alt="Floating agent companions" /></div>;
  return <div className="ob" style={{ "--agent-color": current.color } as CSSProperties}>
    <aside className="ob-nav" aria-label="Main navigation">
      <Link href="/" className="ob-brand"><span className="ob-mark">◒</span><span>Agentic<span className="ob-brand-sub">A LITTLE EXTRA POSSIBILITY</span></span></Link>
      <nav>{[{ href: "/", text: "Observatory", icon: "home" }, { href: "/os", text: "Workspace", icon: "missions" }, { href: "/agents", text: "My agents", icon: "agents" }, { href: "/knowledge", text: "Knowledge", icon: "knowledge" }, { href: "/memory", text: "Memory", icon: "memory" }].map(n => <Link key={n.href} href={n.href} aria-label={n.text} className={n.href === "/" ? "selected" : ""} aria-current={n.href === "/" ? "page" : undefined}><Icon name={n.icon} size={16} /><span>{n.text}</span></Link>)}</nav>
      <div className="ob-nav-bottom"><span className="ob-tiny">MADE FOR YOUR NEXT CHAPTER</span><Link href="/os" className="ob-profile"><span>GJ</span><div>Gaurav<small>Your workspace ↗</small></div></Link></div>
    </aside>
    <div className="ob-world" aria-hidden="true">
      <SceneBoundary fallback={fallback}>{webgl ? <Scene active={active} motion={motion} /> : fallback}</SceneBoundary>
    </div>
    <header className="ob-top"><span><i /> A SPACE FOR YOUR IDEAS</span><button type="button" onClick={() => setMotion(v => !v)} aria-pressed={motion}>{motion ? "Pause motion" : "Enable motion"}<span>{motion ? "Ⅱ" : "▷"}</span></button></header>
    <div className="ob-story">
      <section className="ob-hero" id="welcome">
        <div className="ob-copy"><p className="ob-eyebrow">HUMAN CURIOSITY. A LITTLE AI MAGIC.</p><h1>A little team.<br />A world of<br /><em>possibility.</em></h1><p className="ob-description">Meet the minds that move your work forward.<br />Your ideas, with a little more room to grow.</p><div className="ob-actions"><Link className="ob-button" href="/agents/new">Create an agent <span>↗</span></Link><a href="#peter" className="ob-text-link">Meet the crew ↓</a></div></div>
        <div className="ob-hero-note">Different minds.<br />Beautiful things together.<svg viewBox="0 0 160 90"><path d="M10 6 Q145 -5 120 72 M108 61 L120 72 L132 58" /></svg></div>
        <a href="#peter" className="ob-scroll"><span>01 / EXPLORE YOUR LITTLE UNIVERSE</span><span>SCROLL TO DISCOVER ↓</span></a>
      </section>
      {crew.map((agent, index) => <section id={agent.name.toLowerCase()} data-agent-section={index} className={`ob-chapter ${active === index ? "is-current" : ""}`} key={agent.name} style={{ "--agent-color": agent.color } as CSSProperties}>
        <div className="ob-copy"><p className="ob-eyebrow">0{index + 1} / {agent.role}</p><h2>{agent.title.split("\n").map((line, i) => <span key={line}>{i === 1 ? <em>{line}</em> : line}<br /></span>)}</h2><p className="ob-description">{agent.text}</p><ul className="ob-skills">{agent.skills.map(skill => <li key={skill}><span>✦</span>{skill}</li>)}</ul><Link href={`/agents/new?desc=${encodeURIComponent(agent.prompt)}`} className="ob-button">Create your {agent.name} <span>↗</span></Link></div>
        <div className="ob-intro"><span>{agent.intro}</span><svg viewBox="0 0 200 130"><path d="M12 10 C180 -8 190 50 132 113 M131 96 L132 113 L150 110" /></svg><small>{agent.name.toUpperCase()} / 0{index + 1}</small></div>
      </section>)}
      <section className="ob-ending" data-agent-section={4}><p className="ob-eyebrow">ONE IDEA IS ALL IT TAKES</p><h2>Give your next idea<br /><em>a little company.</em></h2><p>Describe the work. Meet your agent. Make something happen.</p><Link href="/agents/new" className="ob-button">Build your little team <span>↗</span></Link><footer><span>Agentic AI OS</span><a href="#welcome">Back to the stars ↑</a></footer></section>
    </div>
    <nav className="ob-chapters" aria-label="Agent introductions">{crew.map((a, i) => <a href={`#${a.name.toLowerCase()}`} key={a.name} className={active === i ? "active" : ""} aria-label={`Meet ${a.name}`} aria-current={active === i ? "step" : undefined}><i style={{ background: a.color }} /><span>{a.name}</span></a>)}</nav>
  </div>;
}
