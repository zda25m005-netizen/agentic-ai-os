"use client";

import { useEffect, useState } from "react";
import { api, MissionOut } from "./lib/api";
import Topbar from "./components/dashboard/Topbar";
import Hero from "./components/dashboard/Hero";
import AgentCarousel from "./components/dashboard/AgentCarousel";
import MissionProgress from "./components/dashboard/MissionProgress";
import RecentActivity from "./components/dashboard/RecentActivity";
import AIOverview from "./components/dashboard/AIOverview";
import MetricsBar from "./components/dashboard/MetricsBar";

export default function Home() {
  const [missions, setMissions] = useState<MissionOut[] | null>(null);

  useEffect(() => {
    let live = true;
    const load = () => api.listMissions().then((m) => live && setMissions(m)).catch(() => {});
    load();
    const t = setInterval(load, 5000);
    return () => { live = false; clearInterval(t); };
  }, []);

  const running = (missions || []).filter((m) => m.status === "active").length;
  let overrides: Record<string, string> | undefined;
  if (missions && missions.length) {
    const completed = missions.filter((m) => m.status === "completed").length;
    const failed = missions.filter((m) => m.status === "failed").length;
    const terminal = completed + failed;
    overrides = {
      "Total Missions": String(missions.length),
      "Completed": String(completed),
      // success = completed / (completed + failed); consistent with the counts shown
      "Success Rate": terminal ? `${Math.round((completed / terminal) * 100)}%` : "—",
    };
  }

  return (
    <div className="home">
      <Topbar />
      <div className="wrap">
        <Hero running={running} />
        <AgentCarousel />
        <div className="grid3">
          <MissionProgress missions={missions} />
          <RecentActivity />
          <AIOverview />
        </div>
        <MetricsBar overrides={overrides} />
      </div>
    </div>
  );
}
