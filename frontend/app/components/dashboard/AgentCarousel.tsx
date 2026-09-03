"use client";
import { useRef } from "react";
import Link from "next/link";
import Icon from "../Icon";
import { AGENTS } from "../../lib/dashboardData";

export default function AgentCarousel() {
  const ref = useRef<HTMLDivElement>(null);
  const scroll = (dir: number) => ref.current?.scrollBy({ left: dir * 240, behavior: "smooth" });

  return (
    <>
      <div className="sec-head">
        <div className="sec-title">Your Agents</div>
        <div className="sec-nav">
          <button className="icon-btn" onClick={() => scroll(-1)} aria-label="Previous">
            <Icon name="chevronLeft" size={16} sw={2} />
          </button>
          <button className="icon-btn" onClick={() => scroll(1)} aria-label="Next">
            <Icon name="chevronRight" size={16} sw={2} />
          </button>
        </div>
      </div>

      <div className="agents" ref={ref}>
        {AGENTS.map((a, i) => (
          <div key={a.id} className="agent fade-up" style={{ animationDelay: `${i * 40}ms` }}>
            <div className="agent-ico"><Icon name={a.icon} size={20} sw={1.7} /></div>
            <div className="agent-name">{a.name}</div>
            <div className="agent-desc">{a.desc}</div>
            <Link href={a.href} className="agent-btn">
              Open Agent <Icon name="arrowRight" size={13} sw={2} />
            </Link>
          </div>
        ))}
      </div>
    </>
  );
}
