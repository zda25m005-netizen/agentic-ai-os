"use client";

// The continuous spatial world (from the first agent introduction onward). Composition
// is governed by focus weight: each region is prominent only inside its own scroll window
// (world.focusW) and otherwise falls away via focus + distance + fog. At any scroll point
// there is ONE hero object, one supporting text group, and only a few faint secondaries.
// All per-frame work uses refs — never React state.

import { Line, Text, useTexture } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef, type MutableRefObject } from "react";
import * as THREE from "three";
import {
  AGENTS_WORLD, AGENT_HALF, ARTIFACT, BRAIN, COL, fade, FINAL_WORDS, focusW, GOVERNANCE,
  HERO_EXIT, LINKS, MEMORY, MISSION, MONUMENTS, PHRASES, phaseOf, toWorld, worldActivation,
  Z, type Cap, type Mon, type V3,
} from "./world";

type Progress = MutableRefObject<number>;

// soft radial-gradient glow texture (a bloom halo, NOT a disc) — shared by all agents.
let GLOW: THREE.CanvasTexture | null = null;
function glowTexture(): THREE.CanvasTexture {
  if (GLOW) return GLOW;
  const c = document.createElement("canvas"); c.width = c.height = 128;
  const g = c.getContext("2d")!;
  const grad = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  grad.addColorStop(0, "rgba(255,255,255,0.9)");
  grad.addColorStop(0.35, "rgba(255,255,255,0.28)");
  grad.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = grad; g.fillRect(0, 0, 128, 128);
  GLOW = new THREE.CanvasTexture(c);
  return GLOW;
}

// ── world-space text: fog-aware material + distance fade + optional focus window ──
function WorldText({
  text, pos, size, color, anchorX = "center", baseOpacity = 1,
  fadeNear = 16, fadeFar = 46, win, rot, progress,
}: {
  text: string; pos: V3; size: number; color: string;
  anchorX?: "left" | "center" | "right"; baseOpacity?: number;
  fadeNear?: number; fadeFar?: number;
  win?: [number, number]; rot?: [number, number]; progress?: Progress;
}) {
  const mat = useRef<THREE.MeshBasicMaterial>(null);
  const grp = useRef<THREE.Group>(null);
  const self = useMemo(() => new THREE.Vector3(pos[0], pos[1], pos[2]), [pos]);
  useFrame(({ camera }) => {
    const m = mat.current, g = grp.current;
    if (!m || !g) return;
    let o = baseOpacity * fade(camera.position.distanceTo(self), fadeNear, fadeFar);
    if (win && progress) o *= focusW(toWorld(progress.current), win[0], win[1], 0.014);
    if (camera.position.z < pos[2] - 8) o = 0;
    m.opacity = o;
    g.visible = o > 0.008;
  });
  return (
    <group ref={grp} position={pos} rotation={rot ? [rot[0], rot[1], 0] : undefined}>
      <Text fontSize={size} anchorX={anchorX} anchorY="middle" letterSpacing={-0.02} maxWidth={size * 12} textAlign={anchorX}>
        {text}
        <meshBasicMaterial ref={mat} attach="material" color={color} transparent opacity={0} toneMapped={false} depthWrite={false} fog />
      </Text>
    </group>
  );
}

function Monuments({ items, progress, fadeNear = 20 }: { items: Mon[]; progress: Progress; fadeNear?: number }) {
  return (
    <>
      {items.map((m, i) => (
        <WorldText key={`${m.t}-${i}`} text={m.t} pos={m.pos} size={m.size} color={m.color}
          anchorX={m.anchorX ?? "center"} baseOpacity={m.opacity ?? 1} fadeNear={fadeNear}
          fadeFar={m.fadeFar ?? 48} win={m.win} rot={m.rot} progress={progress} />
      ))}
    </>
  );
}

// ── a capability word: dim, spatial, gated by its agent's focus (late ones ramp in) ──
function CapWord({ cap, center, color, progress }: { cap: Cap; center: number; color: string; progress: Progress }) {
  const mat = useRef<THREE.MeshBasicMaterial>(null);
  const grp = useRef<THREE.Group>(null);
  useFrame(() => {
    const m = mat.current, g = grp.current; if (!m || !g) return;
    const w = toWorld(progress.current);
    let f = focusW(w, center, AGENT_HALF, 0.02);
    if (cap.late) f *= Math.max(0, (phaseOf(w, center, AGENT_HALF) - 0.55) / 0.45); // appears near the end
    const o = cap.o * f;
    m.opacity = o; g.visible = o > 0.01;
  });
  return (
    <group ref={grp} position={cap.d} rotation={cap.rot ? [cap.rot[0], cap.rot[1], 0] : undefined} visible={false}>
      <Text fontSize={cap.s} letterSpacing={0.06} anchorX="center" anchorY="middle">
        {cap.t}
        <meshBasicMaterial ref={mat} attach="material" color={color} transparent opacity={0} toneMapped={false} depthWrite={false} fog />
      </Text>
    </group>
  );
}

// ── one agent: PRIMARY mascot + soft glow, SECONDARY quote+arrow+label, few words ──
// The quote and the agent name are ONE stacked typographic component (quote, gap, name
// below) so the label can never land inside the sentence; the arrow leaves from below it.
const QS = 0.4, LH = 1.16;           // quote font size + line height (world units)
function AgentBody({ a, index, texture, progress }: { a: typeof AGENTS_WORLD[number]; index: number; texture: THREE.Texture; progress: Progress }) {
  const grp = useRef<THREE.Group>(null);
  const plane = useRef<THREE.Mesh>(null);
  const planeMat = useRef<THREE.MeshBasicMaterial>(null);
  const glowMat = useRef<THREE.MeshBasicMaterial>(null);
  const annot = useRef<THREE.Group>(null);
  const quoteMat = useRef<THREE.MeshBasicMaterial>(null);
  const nameMat = useRef<THREE.MeshBasicMaterial>(null);
  const armMat = useRef<THREE.MeshBasicMaterial>(null);
  const coneMat = useRef<THREE.MeshBasicMaterial>(null);
  const self = useMemo(() => new THREE.Vector3(a.pos[0], a.pos[1], a.pos[2]), [a.pos]);

  // stacked text block geometry
  const anchorX = a.side === "right" ? "right" : a.side === "center" ? "center" : "left";
  const ax = a.side === "left" ? 2.8 : a.side === "right" ? -2.8 : 0;   // block x (mascot at 0)
  const az = a.side === "center" ? 0.7 : 0.6;
  const quoteTopY = 2.35;
  const lines = a.quote.split("\n").length;
  const nameY = quoteTopY - lines * QS * LH - 0.3;                       // name sits BELOW the quote
  const head: V3 = [0, 1.35, 0.15];
  const start: V3 = [ax, nameY - 0.32, az];                             // arrow leaves below the block
  const connector = useMemo(() => {
    const s = new THREE.Vector3(start[0], start[1], start[2]);
    const e = new THREE.Vector3(head[0], head[1], head[2]);
    const c = new THREE.Vector3((s.x + e.x) / 2 + (a.side === "left" ? -0.5 : 0.5), (s.y + e.y) / 2 + 0.2, (s.z + e.z) / 2 + 0.2);
    return new THREE.TubeGeometry(new THREE.QuadraticBezierCurve3(s, c, e), 22, 0.016, 6, false);
  }, [start[0], start[1], start[2], a.side]);
  const coneQ = useMemo(() => {
    const dir = new THREE.Vector3(head[0] - start[0], head[1] - start[1], head[2] - start[2]).normalize();
    return new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
  }, [start[0], start[1], start[2]]);

  useFrame(({ camera, clock }) => {
    const g = grp.current; if (!g) return;
    const p = progress.current;
    const act = worldActivation(p);                          // 0 during hero → world stays hidden
    const w = toWorld(p);
    const f = focusW(w, a.focus, AGENT_HALF, 0.035);         // this agent owns the frame
    const present = fade(camera.position.distanceTo(self), 6, 40);
    const passed = camera.position.z < a.pos[2] - 6;
    g.visible = act > 0.001 && present > 0.01 && !passed;
    if (!g.visible) return;
    const bob = Math.sin(clock.elapsedTime * 0.8 + index) * 0.11;
    // mascot: faint teaser when approaching (~0.2), full only when focused — all gated by act
    const mo = act * present * (0.2 + 0.8 * f);
    if (plane.current) {
      plane.current.position.y = bob;
      plane.current.scale.setScalar(a.scale * (1 + f * 0.05));
      plane.current.rotation.z = Math.sin(clock.elapsedTime * 0.5 + index) * 0.014;
    }
    if (planeMat.current) planeMat.current.opacity = mo;
    if (glowMat.current) glowMat.current.opacity = mo * 0.13;   // ambient light, not a disc
    const fa = f * act;
    if (annot.current) annot.current.visible = fa > 0.05;
    if (quoteMat.current) quoteMat.current.opacity = fa;
    if (nameMat.current) nameMat.current.opacity = fa * 0.85;
    if (armMat.current) armMat.current.opacity = fa * 0.5;
    if (coneMat.current) coneMat.current.opacity = fa * 0.8;
  });

  return (
    <group ref={grp} position={a.pos} visible={false}>
      {/* soft volumetric glow — a bloom halo (elongated + faint), no hard circular edge */}
      <mesh position={[0, 0.25, -0.5]}>
        <planeGeometry args={[a.scale * 2.9, a.scale * 3.9]} />
        <meshBasicMaterial ref={glowMat} map={glowTexture()} color={a.color} transparent opacity={0}
          depthWrite={false} toneMapped={false} blending={THREE.AdditiveBlending} />
      </mesh>
      <mesh ref={plane}>
        <planeGeometry args={[1, 1.2]} />
        <meshBasicMaterial ref={planeMat} map={texture} transparent depthWrite={false} opacity={0} toneMapped={false} />
      </mesh>

      {/* SECONDARY: one stacked component (quote → gap → name) + clean arrow from below it */}
      <group ref={annot}>
        <mesh geometry={connector}>
          <meshBasicMaterial ref={armMat} color={a.color} transparent opacity={0} toneMapped={false} depthWrite={false} />
        </mesh>
        <mesh position={head} quaternion={coneQ}>
          <coneGeometry args={[0.06, 0.16, 8]} />
          <meshBasicMaterial ref={coneMat} color={a.color} transparent opacity={0} toneMapped={false} depthWrite={false} />
        </mesh>
        <Text position={[ax, quoteTopY, az]} fontSize={QS} anchorX={anchorX} anchorY="top"
          maxWidth={4.6} lineHeight={LH} textAlign={anchorX === "right" ? "right" : "left"}>
          {a.quote}
          <meshBasicMaterial ref={quoteMat} attach="material" color="#eef2f8" transparent opacity={0} toneMapped={false} depthWrite={false} fog />
        </Text>
        <Text position={[ax, nameY, az]} fontSize={0.26} letterSpacing={0.2} anchorX={anchorX} anchorY="top">
          {a.id.toUpperCase()}
          <meshBasicMaterial ref={nameMat} attach="material" color={a.color} transparent opacity={0} toneMapped={false} depthWrite={false} fog />
        </Text>
      </group>

      {/* TERTIARY: only a few dim capability words, spread into depth */}
      {a.words.map((cap) => <CapWord key={cap.t} cap={cap} center={a.focus} color={COL.word} progress={progress} />)}
    </group>
  );
}

function WorldAgents({ progress }: { progress: Progress }) {
  const textures = useTexture(AGENTS_WORLD.map((a) => a.img));
  return <>{AGENTS_WORLD.map((a, i) => <AgentBody key={a.id} a={a} index={i} texture={textures[i]} progress={progress} />)}</>;
}

// ── atmosphere: dim data-dust across the whole journey ──────────────────────────
function Atmosphere() {
  const N = 1200;
  const ref = useRef<THREE.Points>(null);
  const geo = useMemo(() => {
    const arr = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) {
      arr[i * 3] = (Math.random() - 0.5) * 44;
      arr[i * 3 + 1] = (Math.random() - 0.5) * 26;
      arr[i * 3 + 2] = 8 - Math.random() * 330;
    }
    return arr;
  }, []);
  useFrame(({ clock }) => { if (ref.current) ref.current.rotation.z = Math.sin(clock.elapsedTime * 0.02) * 0.04; });
  return (
    <points ref={ref}>
      <bufferGeometry><bufferAttribute attach="attributes-position" args={[geo, 3]} /></bufferGeometry>
      <pointsMaterial color="#333c50" size={0.045} transparent opacity={0.45} sizeAttenuation depthWrite={false} fog />
    </points>
  );
}

// ── communication packets between agents (only in the communication region) ─────
function Packets({ progress }: { progress: Progress }) {
  const COUNT = LINKS.length;
  const ref = useRef<THREE.Points>(null);
  const grp = useRef<THREE.Group>(null);
  const curves = useMemo(() => LINKS.map((l) => {
    const s = AGENTS_WORLD.find((a) => a.id === l.from)!.pos;
    const start = new THREE.Vector3(s[0], s[1], s[2]);
    const end = new THREE.Vector3(l.to[0], l.to[1], l.to[2]);
    const mid = start.clone().lerp(end, 0.5).add(new THREE.Vector3((Math.random() - 0.5) * 4, 2 + Math.random() * 2, 0));
    return new THREE.QuadraticBezierCurve3(start, mid, end);
  }), []);
  const buf = useMemo(() => new Float32Array(COUNT * 3), [COUNT]);
  const tRef = useRef(curves.map(() => Math.random()));
  const tmp = useMemo(() => new THREE.Vector3(), []);
  useFrame((_s, dt) => {
    const w = toWorld(progress.current);
    const on = w > 0.6 && w < 0.665;
    if (grp.current) grp.current.visible = on;
    if (!on || !ref.current) return;
    for (let i = 0; i < COUNT; i++) {
      tRef.current[i] = (tRef.current[i] + dt * (0.12 + i * 0.03)) % 1;
      curves[i].getPoint(tRef.current[i], tmp);
      buf[i * 3] = tmp.x; buf[i * 3 + 1] = tmp.y; buf[i * 3 + 2] = tmp.z;
    }
    (ref.current.geometry.attributes.position as THREE.BufferAttribute).needsUpdate = true;
  });
  return (
    <group ref={grp} visible={false}>
      {curves.map((c, i) => (
        <Line key={i} points={c.getPoints(24)} color={LINKS[i].color} transparent opacity={0.22} lineWidth={1} />
      ))}
      <points ref={ref}>
        <bufferGeometry><bufferAttribute attach="attributes-position" args={[buf, 3]} /></bufferGeometry>
        <pointsMaterial color={COL.accent} size={0.26} transparent opacity={0.95} depthWrite={false} sizeAttenuation />
      </points>
    </group>
  );
}

function MissionWorld({ progress }: { progress: Progress }) {
  const grp = useRef<THREE.Group>(null);
  const orb = useRef<THREE.Mesh>(null);
  const splitRefs = useRef<(THREE.Group | null)[]>([]);
  const dirs = useMemo(() => MISSION.splits.map((_, i) => {
    const ang = (i / MISSION.splits.length) * Math.PI * 2;
    return new THREE.Vector3(Math.cos(ang) * 4.5, Math.sin(ang) * 3, -1 - Math.random() * 2);
  }), []);
  useFrame(() => {
    const w = toWorld(progress.current);
    const on = w > 0.73 && w < 0.9;
    if (grp.current) grp.current.visible = on;
    if (!on) return;
    const approach = THREE.MathUtils.clamp((w - 0.73) / 0.07, 0, 1);
    const split = THREE.MathUtils.clamp((w - 0.80) / 0.06, 0, 1);
    if (orb.current) {
      orb.current.position.z = THREE.MathUtils.lerp(-14, 0, approach);
      orb.current.scale.setScalar(0.6 * (1 - split * 0.6));
      (orb.current.material as THREE.MeshBasicMaterial).opacity = (1 - split) * approach;
    }
    MISSION.splits.forEach((_, i) => {
      const g = splitRefs.current[i]; if (!g) return;
      g.position.set(dirs[i].x * split, dirs[i].y * split, dirs[i].z * split);
      g.visible = split > 0.05;
    });
  });
  return (
    <group ref={grp} position={MISSION.pos} visible={false}>
      <mesh ref={orb}><icosahedronGeometry args={[1, 1]} /><meshBasicMaterial color={COL.accent} transparent opacity={0} toneMapped={false} /></mesh>
      <Text position={[0, -1.6, 0.2]} fontSize={0.5} anchorX="center" anchorY="top" maxWidth={7} lineHeight={1.2} textAlign="center">
        {`NEW MISSION\n${MISSION.brief}`}
        <meshBasicMaterial attach="material" color="#e7edf6" transparent toneMapped={false} depthWrite={false} fog />
      </Text>
      {MISSION.splits.map((s, i) => (
        <group key={s} ref={(el) => { splitRefs.current[i] = el; }} visible={false}>
          <Text fontSize={0.44} anchorX="center">
            {s}
            <meshBasicMaterial attach="material" color={COL.accent} transparent opacity={0.9} toneMapped={false} depthWrite={false} fog />
          </Text>
        </group>
      ))}
    </group>
  );
}

function BrainWorld({ progress }: { progress: Progress }) {
  const grp = useRef<THREE.Group>(null);
  const signal = useRef<THREE.Mesh>(null);
  const ring = useMemo(() => BRAIN.parts.map((t, i) => {
    const ang = (i / BRAIN.parts.length) * Math.PI * 2;
    return { t, p: [Math.cos(ang) * 4, Math.sin(ang) * 2.4, Math.sin(ang * 2) * 1.5] as V3 };
  }), []);
  const edges = useMemo(() => {
    const arr = new Float32Array(ring.length * 6);
    ring.forEach((n, i) => { const nx = ring[(i + 1) % ring.length]; arr.set([n.p[0], n.p[1], n.p[2], nx.p[0], nx.p[1], nx.p[2]], i * 6); });
    return arr;
  }, [ring]);
  useFrame(({ clock }) => {
    const w = toWorld(progress.current);
    const on = w > 0.855 && w < 0.915;
    if (grp.current) { grp.current.visible = on; grp.current.rotation.y = clock.elapsedTime * 0.05; }
    if (!on || !signal.current) return;
    const k = ring.length, tt = (clock.elapsedTime * 0.5) % k;
    const i = Math.floor(tt), f = tt - i, aa = ring[i], bb = ring[(i + 1) % k];
    signal.current.position.set(THREE.MathUtils.lerp(aa.p[0], bb.p[0], f), THREE.MathUtils.lerp(aa.p[1], bb.p[1], f), THREE.MathUtils.lerp(aa.p[2], bb.p[2], f));
  });
  return (
    <group ref={grp} position={BRAIN.center} visible={false}>
      <lineSegments>
        <bufferGeometry><bufferAttribute attach="attributes-position" args={[edges, 3]} /></bufferGeometry>
        <lineBasicMaterial color="#3b4a6a" transparent opacity={0.5} fog />
      </lineSegments>
      {ring.map((n) => (
        <group key={n.t} position={n.p}>
          <mesh><icosahedronGeometry args={[0.32, 1]} /><meshBasicMaterial color="#7aa2ff" transparent opacity={0.85} toneMapped={false} /></mesh>
          <Text position={[0, 0.58, 0]} fontSize={0.28} anchorX="center">
            {n.t}
            <meshBasicMaterial attach="material" color="#c9d3e0" transparent toneMapped={false} depthWrite={false} fog />
          </Text>
        </group>
      ))}
      <mesh ref={signal}><sphereGeometry args={[0.13, 12, 12]} /><meshBasicMaterial color={COL.accent} toneMapped={false} /></mesh>
    </group>
  );
}

function MemoryWorld({ progress }: { progress: Progress }) {
  const grp = useRef<THREE.Group>(null);
  const clusters = useMemo(() => MEMORY.clusters.map((c) => {
    const M = 240; const arr = new Float32Array(M * 3);
    for (let i = 0; i < M; i++) {
      const r = Math.pow(Math.random(), 0.5) * 1.8, th = Math.random() * Math.PI * 2, ph = Math.acos(2 * Math.random() - 1);
      arr[i * 3] = c.d[0] + r * Math.sin(ph) * Math.cos(th);
      arr[i * 3 + 1] = c.d[1] + r * Math.sin(ph) * Math.sin(th);
      arr[i * 3 + 2] = c.d[2] + r * Math.cos(ph);
    }
    return { ...c, arr };
  }), []);
  const mats = useRef<(THREE.PointsMaterial | null)[]>([]);
  useFrame(({ clock }) => {
    const w = toWorld(progress.current);
    const on = w > 0.905 && w < 0.95;
    if (grp.current) grp.current.visible = on;
    if (!on) return;
    clusters.forEach((_, i) => {
      const m = mats.current[i]; if (!m) return;
      const pulse = 0.4 + 0.6 * (0.5 + 0.5 * Math.sin(clock.elapsedTime * 1.2 - i * 1.3));
      m.opacity = 0.35 + pulse * 0.5; m.size = 0.05 + pulse * 0.04;
    });
  });
  return (
    <group ref={grp} position={MEMORY.center} visible={false}>
      {clusters.map((c, i) => (
        <group key={c.t}>
          <points>
            <bufferGeometry><bufferAttribute attach="attributes-position" args={[c.arr, 3]} /></bufferGeometry>
            <pointsMaterial ref={(el) => { mats.current[i] = el; }} color={c.color} size={0.06} transparent opacity={0.5} sizeAttenuation depthWrite={false} fog />
          </points>
          <Text position={[c.d[0], c.d[1] + 2.2, c.d[2]]} fontSize={0.42} anchorX="center">
            {c.t}
            <meshBasicMaterial attach="material" color={c.color} transparent toneMapped={false} depthWrite={false} fog />
          </Text>
        </group>
      ))}
    </group>
  );
}

function GovernanceWorld({ progress }: { progress: Progress }) {
  const grp = useRef<THREE.Group>(null);
  const left = useRef<THREE.Mesh>(null);
  const right = useRef<THREE.Mesh>(null);
  useFrame(() => {
    const w = toWorld(progress.current);
    const on = w > 0.94 && w < 0.975;
    if (grp.current) grp.current.visible = on;
    if (!on) return;
    const close = THREE.MathUtils.clamp((w - 0.94) / 0.022, 0, 1);
    const open = THREE.MathUtils.clamp((w - 0.965) / 0.01, 0, 1);
    const gap = THREE.MathUtils.lerp(3.4, 0.5, close) + open * 6;
    if (left.current) left.current.position.x = -gap;
    if (right.current) right.current.position.x = gap;
  });
  return (
    <group ref={grp} position={[0, 0, GOVERNANCE.gateZ]} visible={false}>
      {GOVERNANCE.words.map((wd) => (
        <WorldText key={wd.t} text={wd.t} pos={[wd.pos[0], wd.pos[1], wd.pos[2]]} size={wd.size} color={COL.policy} fadeNear={14} fadeFar={55} />
      ))}
      <mesh ref={left} position={[-3.4, 0, 0]}><boxGeometry args={[3, 7, 0.3]} /><meshStandardMaterial color="#12161d" emissive={COL.policy} emissiveIntensity={0.25} metalness={0.4} roughness={0.5} /></mesh>
      <mesh ref={right} position={[3.4, 0, 0]}><boxGeometry args={[3, 7, 0.3]} /><meshStandardMaterial color="#12161d" emissive={COL.policy} emissiveIntensity={0.25} metalness={0.4} roughness={0.5} /></mesh>
    </group>
  );
}

function ArtifactWorld({ progress }: { progress: Progress }) {
  const grp = useRef<THREE.Group>(null);
  const pts = useRef<THREE.Points>(null);
  const panel = useRef<THREE.Mesh>(null);
  const N = 380;
  const seed = useMemo(() => {
    const from = new Float32Array(N * 3), cur = new Float32Array(N * 3), to = new Float32Array(N * 3);
    for (let i = 0; i < N; i++) {
      from[i * 3] = (Math.random() - 0.5) * 20; from[i * 3 + 1] = (Math.random() - 0.5) * 14; from[i * 3 + 2] = (Math.random() - 0.5) * 18;
      cur.set([from[i * 3], from[i * 3 + 1], from[i * 3 + 2]], i * 3);
      to[i * 3] = (Math.random() - 0.5) * 2.4; to[i * 3 + 1] = (Math.random() - 0.5) * 3.2; to[i * 3 + 2] = (Math.random() - 0.5) * 0.2;
    }
    return { from, cur, to };
  }, []);
  useFrame(() => {
    const w = toWorld(progress.current);
    const on = w > 0.965 && w <= 1.0;
    if (grp.current) grp.current.visible = on;
    if (!on || !pts.current) return;
    const form = THREE.MathUtils.clamp((w - 0.965) / 0.017, 0, 1);
    const { from, cur, to } = seed;
    for (let i = 0; i < N * 3; i++) cur[i] = THREE.MathUtils.lerp(from[i], to[i], form);
    (pts.current.geometry.attributes.position as THREE.BufferAttribute).needsUpdate = true;
    if (panel.current) (panel.current.material as THREE.MeshBasicMaterial).opacity = form * 0.12;
  });
  return (
    <group ref={grp} position={ARTIFACT.center} visible={false}>
      <mesh ref={panel}><planeGeometry args={[2.6, 3.4]} /><meshBasicMaterial color={COL.accent} transparent opacity={0} depthWrite={false} toneMapped={false} /></mesh>
      <points ref={pts}>
        <bufferGeometry><bufferAttribute attach="attributes-position" args={[seed.cur, 3]} /></bufferGeometry>
        <pointsMaterial color={COL.accent} size={0.07} transparent opacity={0.9} sizeAttenuation depthWrite={false} />
      </points>
      <Text position={[0, -2.4, 0.2]} fontSize={0.5} anchorX="center">
        {ARTIFACT.label}
        <meshBasicMaterial attach="material" color="#e7edf6" transparent toneMapped={false} depthWrite={false} fog />
      </Text>
    </group>
  );
}

function FinalReveal({ progress }: { progress: Progress }) {
  return (
    <>
      <Monuments items={FINAL_WORDS} progress={progress} fadeNear={40} />
      <WorldText text="Planning · Tools · Memory · Governance · Recovery · Evaluation"
        pos={[0, -8.5, Z.final + 4]} size={0.85} color={COL.word} anchorX="center" fadeNear={26} fadeFar={90} progress={progress} />
    </>
  );
}

export default function SpatialWorld({ progress }: { progress: Progress }) {
  const root = useRef<THREE.Group>(null);
  // ONE post-hero activation gate: the whole world is hidden until the hero has fully left.
  useFrame(() => { if (root.current) root.current.visible = progress.current >= HERO_EXIT; });
  return (
    <group ref={root} visible={false}>
      <Atmosphere />
      <WorldAgents progress={progress} />
      <Monuments items={MONUMENTS} progress={progress} />
      <Monuments items={PHRASES} progress={progress} fadeNear={16} />
      <Packets progress={progress} />
      <MissionWorld progress={progress} />
      <BrainWorld progress={progress} />
      <MemoryWorld progress={progress} />
      <GovernanceWorld progress={progress} />
      <ArtifactWorld progress={progress} />
      <FinalReveal progress={progress} />
    </group>
  );
}
