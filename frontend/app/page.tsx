"use client";

// World 1 — cinematic public landing at /. Full-bleed; the sidebar hides itself on "/".
// The experience is client-only (WebGL + smooth scroll), so it's dynamically imported
// with SSR off; the semantic copy still renders inside it for accessibility.

import dynamic from "next/dynamic";
import "./experience/experience.css";

const ExperienceRoot = dynamic(() => import("./experience/ExperienceRoot"), { ssr: false });

export default function LandingPage() {
  return <ExperienceRoot />;
}
