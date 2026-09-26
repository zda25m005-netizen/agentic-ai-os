"use client";

// The observatory owns its unified navigation and persistent WebGL scene.

import dynamic from "next/dynamic";
import "./observatory/observatory.css";

const ExperienceRoot = dynamic(() => import("./observatory/Observatory"), { ssr: false });

export default function LandingPage() {
  return <ExperienceRoot />;
}
