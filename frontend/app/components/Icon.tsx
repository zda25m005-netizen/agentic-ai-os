import React from "react";

// Minimal inline SVG icon set (no external icon dependency).
const PATHS: Record<string, React.ReactNode> = {
  logo: <path d="M12 3l7 4v6c0 4-3 6.5-7 8-4-1.5-7-4-7-8V7l7-4z" />,
  home: <><path d="M3 10.5 12 3l9 7.5" /><path d="M5 9v11h14V9" /></>,
  missions: <><path d="M8 6h13M8 12h13M8 18h13" /><path d="M3 6l1 1 1.5-1.5M3 12l1 1 1.5-1.5M3 18l1 1 1.5-1.5" /></>,
  agents: <><circle cx="12" cy="6" r="2.5" /><circle cx="5" cy="18" r="2.5" /><circle cx="19" cy="18" r="2.5" /><path d="M12 8.5v3M11 13l-4 3M13 13l4 3" /></>,
  memory: <><path d="M9 4a3 3 0 0 0-3 3 3 3 0 0 0-1 5 3 3 0 0 0 2 5 2.5 2.5 0 0 0 5 .5V5a2 2 0 0 0-3-1z" /><path d="M15 4a3 3 0 0 1 3 3 3 3 0 0 1 1 5 3 3 0 0 1-2 5 2.5 2.5 0 0 1-5 .5" /></>,
  knowledge: <><path d="M4 5.5A2 2 0 0 1 6 4h6v16H6a2 2 0 0 0-2 1.5z" /><path d="M20 5.5A2 2 0 0 0 18 4h-6v16h6a2 2 0 0 1 2 1.5z" /></>,
  tools: <path d="M14.5 5.5a3.5 3.5 0 0 0-5 4.5L4 15.5 8.5 20l5.5-5.5a3.5 3.5 0 0 0 4.5-5l-2.5 2.5-2-2 2.5-2.5z" />,
  evaluations: <><rect x="5" y="3" width="14" height="18" rx="2" /><path d="M9 8l1.5 1.5L13 7M9 14l1.5 1.5L13 13" /></>,
  observability: <path d="M3 12h4l2 6 4-14 2 8h6" />,
  jobsearch: <><circle cx="11" cy="11" r="6" /><path d="M20 20l-3.5-3.5" /></>,
  research: <><path d="M5 4h11l3 3v13H5z" /><path d="M8 9h7M8 13h7M8 17h4" /></>,
  person: <><circle cx="12" cy="8" r="3.2" /><path d="M5.5 20a6.5 6.5 0 0 1 13 0" /></>,
  cap: <><path d="M12 4 2 9l10 5 8-4v6" /><path d="M6 12v4c0 1.5 3 3 6 3s6-1.5 6-3v-4" /></>,
  globe: <><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3c2.5 2.5 2.5 15 0 18M12 3c-2.5 2.5-2.5 15 0 18" /></>,
  settings: <><circle cx="12" cy="12" r="3" /><path d="M19 12a7 7 0 0 0-.1-1.2l2-1.5-2-3.4-2.3 1a7 7 0 0 0-2-1.2l-.4-2.5H10.8l-.4 2.5a7 7 0 0 0-2 1.2l-2.3-1-2 3.4 2 1.5A7 7 0 0 0 5 12a7 7 0 0 0 .1 1.2l-2 1.5 2 3.4 2.3-1a7 7 0 0 0 2 1.2l.4 2.5h2.4l.4-2.5a7 7 0 0 0 2-1.2l2.3 1 2-3.4-2-1.5A7 7 0 0 0 19 12z" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="M21 21l-4-4" /></>,
  bell: <><path d="M6 9a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6z" /><path d="M10 19a2 2 0 0 0 4 0" /></>,
  chevronDown: <path d="M6 9l6 6 6-6" />,
  chevronLeft: <path d="M15 6l-6 6 6 6" />,
  chevronRight: <path d="M9 6l6 6-6 6" />,
  arrowRight: <path d="M5 12h14M13 6l6 6-6 6" />,
  running: <path d="M4 6h16M4 12h16M4 18h16" />,
  sync: <path d="M4 12a8 8 0 0 1 14-5l2 2M20 12a8 8 0 0 1-14 5l-2-2" />,
  resume: <><path d="M6 3h9l4 4v14H6z" /><path d="M9 12h6M9 16h6" /></>,
  chart: <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />,
  check: <><circle cx="12" cy="12" r="9" /><path d="M8 12l3 3 5-6" /></>,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  pin: <><path d="M12 17v5" /><path d="M9 3h6l-1 6 3 3H7l3-3-1-6z" /></>,
  more: <><circle cx="5" cy="12" r="1.4" /><circle cx="12" cy="12" r="1.4" /><circle cx="19" cy="12" r="1.4" /></>,
  plus: <path d="M12 5v14M5 12h14" />,
  alert: <><path d="M12 3l9 16H3z" /><path d="M12 10v4M12 17v.5" /></>,
  edit: <><path d="M4 20h4L18 10l-4-4L4 16z" /><path d="M13.5 6.5l4 4" /></>,
  trash: <><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13" /></>,
  x: <path d="M6 6l12 12M18 6L6 18" />,
  calc: <><rect x="5" y="3" width="14" height="18" rx="2" /><path d="M8 7h8M8 11h2M12 11h4M8 15h2M12 15h4" /></>,
  code: <><path d="M9 7l-5 5 5 5M15 7l5 5-5 5" /></>,
  database: <><ellipse cx="12" cy="6" rx="7" ry="2.6" /><path d="M5 6v12c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6V6M5 12c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6" /></>,
  file: <><path d="M6 3h8l4 4v14H6z" /><path d="M14 3v4h4" /></>,
  users: <><circle cx="9" cy="8" r="3" /><path d="M3.5 20a5.5 5.5 0 0 1 11 0" /><path d="M16 5.2a3 3 0 0 1 0 5.6M17 20a5.5 5.5 0 0 0-3-4.9" /></>,
  shield: <><path d="M12 3l7 3v6c0 4-3 6.5-7 8-4-1.5-7-4-7-8V6l7-3z" /><path d="M9 12l2 2 4-4" /></>,
  bookmark: <path d="M6 3h12v18l-6-4-6 4z" />,
  bookmarkOn: <path d="M6 3h12v18l-6-4-6 4z" fill="currentColor" stroke="currentColor" />,
  filter: <path d="M3 5h18l-7 8v6l-4-2v-4z" />,
  mapPin: <><path d="M12 21s7-5.5 7-11a7 7 0 0 0-14 0c0 5.5 7 11 7 11z" /><circle cx="12" cy="10" r="2.5" /></>,
  briefcase: <><rect x="3" y="7" width="18" height="13" rx="2" /><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18" /></>,
  layers: <><path d="M12 3l9 5-9 5-9-5z" /><path d="M3 13l9 5 9-5" /></>,
  external: <><path d="M14 4h6v6M20 4l-8 8" /><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" /></>,
};

export default function Icon({ name, size = 16, sw = 1.8, style }: {
  name: string; size?: number; sw?: number; style?: React.CSSProperties;
}) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none"
      stroke="currentColor" strokeWidth={sw} strokeLinecap="round"
      strokeLinejoin="round" style={style} aria-hidden>
      {PATHS[name] || null}
    </svg>
  );
}
