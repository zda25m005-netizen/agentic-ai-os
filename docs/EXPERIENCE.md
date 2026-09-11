# EXPERIENCE.md — Agent Universe (World 1) + Control Plane (World 2)

The frontend has two worlds:

- **World 1 — public experience** (`/`): a cinematic, scroll-driven agent universe. One
  persistent WebGL canvas (React Three Fiber) behind semantic HTML scenes; smooth scroll via
  Lenis; a single normalized scroll progress (0→1) drives the camera. All copy is real HTML,
  so `prefers-reduced-motion` drops the canvas + animation and keeps the content.
- **World 2 — control plane** (`/os` and the rest of the app): the working agent dashboard.
  Functional first, subtle depth/character animation only.

Routing: `/` = landing (sidebar hidden), `/os` = dashboard (moved from `/`). All other deep
links (`/agents`, `/missions`, `/memory`, …) unchanged.

## Tech (installed this pass)

`three@0.169`, `@react-three/fiber@8`, `@react-three/drei@9`, `lenis@1`. One `<Canvas>`,
`dpr=[1,1.8]`, `alpha`, high-performance. Frame work happens in `useFrame` reading a
progress **ref** (never React state) → 60fps. Mascots are the real 3D renders, edge-cut to
transparent (`public/mascots/*-cut.webp`) so they float on the dark universe.

## Component tree (World 1)

```
app/page.tsx  (client, dynamic ssr:false)
└─ experience/ExperienceRoot   Lenis + scroll progress + reduced-motion + scene overlays
   ├─ experience/AgentWorld     R3F <Canvas>: Stars + AgentNode(Float) + Links + Rig(camera)
   └─ scenes.ts                 crew roster + hero labels (data only)
experience/experience.css        full-bleed scene styling + reduced-motion fallbacks
```

## Scene map (guideline scroll ranges)

| # | Scroll | Scene | Copy | Characters / objects | Camera | Interaction | Mobile fallback | Status |
|---|--------|-------|------|----------------------|--------|-------------|-----------------|--------|
| 01 | .00–.10 | Boot / Hero | BUILD AGENTS. GIVE THEM TOOLS. LET THEM WORK. / "Your AI workforce starts here." | starfield, glowing agent nodes, floating status labels | dolly-in from z=8 | CTAs → /agents/new, /os; cursor parallax | static hero, fewer labels | **built** |
| 02 | .10–.20 | Meet the agents | "They're not mascots. They're agents." | Scout/Analyst/Researcher/Memory cutouts + taglines | slight lateral drift | hover lift + glow, click → builder | 1–2 col grid, no float | **built** |
| 03 | .20–.30 | Create your own | DON'T JUST USE AI. BUILD ONE. | agent assembles: core→role→brain→tools→memory→rules→ready | push toward input | typed spec preview | simplified stack list | planned |
| 04 | .30–.37 | Give it a brain | (real: planner→executor→critic) | neural core, LLM/PLANNER/MEMORY/KNOWLEDGE/TOOLS/POLICY/CRITIC | camera enters agent | pulse on hover | static diagram | planned |
| 05 | .37–.45 | Tool orbit | GIVE YOUR AGENT HANDS. | tools orbit (Web/Python/SQL/RAG/Graph/Files/HTTP/Wikipedia/data/subagents) | pull back | beam on hover | ring → row | planned |
| 06 | .45–.53 | Memory | YOUR AGENTS REMEMBER. | working/episodic/semantic/procedural/organizational fragments | travel through field | retrieval glow | fewer fragments | planned |
| 07 | .53–.61 | Collaboration | ONE AGENT IS USEFUL. A TEAM CHANGES EVERYTHING. | planner→researcher/browser/analyst→critic, info packets | widen | packet follow cursor | static graph | planned |
| 08 | .61–.68 | The critic | THEY CHECK THEIR OWN WORK. | Guardian scan → APPROVED / RETRY | hold | scan sweep | static states | planned |
| 09 | .68–.75 | Governed execution | AUTONOMOUS. NOT UNCONTROLLED. | gates: registry→policy→approval→budget→exec→verify→artifact | gate corridor | approval card ALLOW/DENY | vertical steps | planned |
| 10 | .75–.82 | Missions | GIVE THEM GOALS. NOT PROMPTS. | mission decomposition, concurrent tasks, one FAIL→RECOVER | overhead | none | list tree | planned |
| 11 | .82–.88 | Use cases | (research/job/phd/data/coding/travel/document) | 3D carousel of missions | orbit | drag carousel | swipe row | planned |
| 12 | .88–.92 | Artifacts | YOUR AGENTS BRING BACK RESULTS. | agent returns with PDF/CSV/report/booking | toward viewer | none | static | planned |
| 13 | .92–.96 | OS reveal | BEHIND EVERY CUTE AGENT IS A SERIOUS RUNTIME. | pull back to full system graph | dramatic dolly-out | none | fade | **bridge built** |
| 14 | .96–1.0 | Enter mission control | — | dashboard preview | settle | ENTER → /os | button | link built |
| 15 | (route) | Agent builder | — | live character reacts to config | — | /agents/new | full form | exists (Phase 5) |

## Real-architecture mapping (no invented systems)

Brain = LangGraph planner→executor→critic. Tools = tool registry. Memory = memory engine
(configs A–G, incl. Config-G learned policy). Collaboration = multi-agent mission runtime.
Governance = governed execution + approval policy. Missions = mission scheduler + recovery.
Artifacts = report/exec outputs. OS reveal = missions/observability/evals.

## Performance + accessibility

Single canvas; instanced/light meshes; `dpr` clamp; lazy mascot images; refs (not state) in
`useFrame`; reduced-motion path renders pure HTML (no WebGL). Mobile: fewer particles/nodes,
no heavy parallax, storytelling preserved via HTML scenes.
