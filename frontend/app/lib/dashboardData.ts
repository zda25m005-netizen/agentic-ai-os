// Static config for the Home dashboard (non-mission content).
export const AGENTS = [
  { id: "job-search", name: "Job Search Agent", desc: "Find and match the best job opportunities.", icon: "jobsearch", href: "/agents/job-search" },
  { id: "research", name: "Research Agent", desc: "Deep research with reliable sources and analysis.", icon: "research", href: "/agents/research" },
  { id: "knowledge", name: "Personal Knowledge Agent", desc: "Manage and leverage your personal knowledge base.", icon: "person", href: "/agents/knowledge" },
  { id: "career", name: "Student Career Agent", desc: "All-in-one career assistant for students.", icon: "cap", href: "/agents/student-career" },
  { id: "browser", name: "Browser / Action Agent", desc: "Browse the web and get things done for you.", icon: "globe", href: "/agents/browser" },
];

export const ACTIVITY = [
  { title: "Research report generated", sub: "RAG vs Fine-tuning Analysis", time: "2m ago", icon: "research" },
  { title: "New job match found", sub: "ML Engineer at DeepMind", time: "15m ago", icon: "jobsearch" },
  { title: "Resume optimized", sub: "ML Engineer Resume v3", time: "1h ago", icon: "resume" },
  { title: "Knowledge base updated", sub: "Added 5 new documents", time: "2h ago", icon: "knowledge" },
];

export const OVERVIEW = [
  { label: "Research", pct: 35, color: "#6EA8FF" },
  { label: "Jobs", pct: 25, color: "#8A9299" },
  { label: "Learning", pct: 20, color: "#5A6169" },
  { label: "Others", pct: 20, color: "#3A3F45" },
];

// Demo defaults are internally consistent: 46 completed / 50 total ≈ 92% success.
export const METRICS = [
  { label: "Total Missions", value: "50", grow: "↑ 12% from last week", icon: "chart" },
  { label: "Completed", value: "46", grow: "↑ 8% from last week", icon: "check" },
  { label: "Success Rate", value: "92%", grow: "↑ 5% from last week", icon: "clock" },
  { label: "Time Saved", value: "120h", grow: "↑ 15h from last week", icon: "clock" },
];

export const QUICK_ACTIONS = ["Research", "Find Jobs", "Analyze", "Create Report", "Take Action"];
