"use client";

// Persistent agent-universe canvas. Scene OWNERSHIP is driven by ./timeline so only one
// beat is visible at a time: the hero is empty space, each agent is staged SOLO, the four
// reunite, then (and only then) the network exists. A cursor force-field disturbs the
// network's micro-nodes. All per-frame work uses refs/typed arrays — never React state.

import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Stars, useTexture } from "@react-three/drei";
import { Suspense, useMemo, useRef, type MutableRefObject } from "react";
import * as THREE from "three";
import { EDGES, GRAPH_CENTER_Z, KIND_COLOR, NODES, NODE_INDEX } from "./graph";
import { BAND, SOLO, local, vis } from "./timeline";

type Progress = MutableRefObject<number>;
type HoverCb = (id: string | null) => void;
export type DebugInfo = { camZ: number; mascots: Record<string, number>; active: string };
type DebugRef = MutableRefObject<DebugInfo> | undefined;

// solo staging (x,y) per agent + which mascot texture, and the team-scene home.
const AGENTS = [
  { id: "researcher", img: "/mascots/rory-3d-cut.webp", solo: [-1.7, 0.1] as const, team: [-2.6, 0.1, 0] as const },
  { id: "planner", img: "/mascots/peter-3d-cut.webp", solo: [1.6, 0.3] as const, team: [0, 0.9, -3] as const },
  { id: "coder", img: "/mascots/ivy-3d-cut.webp", solo: [-1.6, 0.1] as const, team: [2.6, 0.0, -1.5] as const },
  { id: "analyst", img: "/mascots/luna-3d-cut.webp", solo: [0.2, -0.2] as const, team: [0, -1.7, 0.6] as const },
];
const TEAM = BAND.team;

function Mascots({ progress, debug }: { progress: Progress; debug: DebugRef }) {
  const textures = useTexture(AGENTS.map((a) => a.img));
  const meshes = useRef<(THREE.Mesh | null)[]>([]);
  useFrame((state) => {
    const p = progress.current;
    const bob = Math.sin(state.clock.elapsedTime * 0.9);
    AGENTS.forEach((a, i) => {
      const m = meshes.current[i];
      if (!m) return;
      const soloV = vis(p, SOLO[a.id]);
      const teamV = vis(p, TEAM);
      const v = Math.max(soloV, teamV);
      const mat = m.material as THREE.MeshBasicMaterial;
      if (v < 0.01) { m.visible = false; mat.opacity = 0; if (debug) debug.current.mascots[a.id] = 0; return; }
      m.visible = true;
      if (soloV >= teamV) {
        // SOLO: enter from far, settle, drift out sideways
        const lp = local(p, SOLO[a.id]);
        const enter = Math.min(1, lp / 0.4);
        const es = enter * enter * (3 - 2 * enter);
        const exit = lp > 0.78 ? (lp - 0.78) / 0.22 : 0;
        const dir = a.solo[0] >= 0 ? 1 : -1;
        m.position.set(a.solo[0] + exit * dir * 2.4, a.solo[1] + bob * 0.12, THREE.MathUtils.lerp(-5, 0.2, es));
        m.scale.setScalar(2.05);
        mat.opacity = soloV;
      } else {
        // TEAM: spatial home + gentle bob
        m.position.set(a.team[0], a.team[1] + bob * 0.1, a.team[2]);
        m.scale.setScalar(1.35);
        mat.opacity = teamV;
      }
      if (debug) debug.current.mascots[a.id] = Math.round(mat.opacity * 100) / 100;
    });
  });
  return (
    <>
      {AGENTS.map((a, i) => (
        // plane faces +Z toward the camera; no Billboard (that nesting hid the mesh).
        <mesh key={a.id} ref={(el) => { meshes.current[i] = el; }} visible={false} position={[a.solo[0], a.solo[1], -5]}>
          <planeGeometry args={[1, 1.2]} />
          <meshBasicMaterial map={textures[i]} transparent depthWrite={false} opacity={0} toneMapped={false} />
        </mesh>
      ))}
    </>
  );
}

function Network({ progress, onHover }: { progress: Progress; onHover: HoverCb }) {
  const { camera, pointer } = useThree();
  const group = useRef<THREE.Group>(null);
  const inst = useRef<THREE.InstancedMesh | null>(null);
  const hovered = useRef<number | null>(null);
  const lastReported = useRef<string | null>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const colors = useMemo(() => NODES.map((n) => new THREE.Color(KIND_COLOR[n.kind])), []);

  // Major-node physics: rest / current / velocity + per-node idle phase. The cursor is a
  // repulsion field; nodes spring back toward rest with a little overshoot, edges follow.
  const node = useMemo(() => {
    const n = NODES.length;
    const rest = new Float32Array(n * 3);
    const phase = new Float32Array(n);
    NODES.forEach((g, i) => { rest.set(g.pos, i * 3); phase[i] = Math.random() * Math.PI * 2; });
    return { rest, cur: rest.slice(), vel: new Float32Array(n * 3), phase };
  }, []);

  // Edge endpoints as node-index pairs + rest lengths → elastic links so a disturbance
  // ripples through the local neighborhood, plus a live buffer the line mesh renders.
  const edge = useMemo(() => {
    const pairs: [number, number][] = EDGES.map(([a, b]) => [NODE_INDEX[a], NODE_INDEX[b]]);
    const restLen = new Float32Array(pairs.length);
    const pos = new Float32Array(pairs.length * 6);
    pairs.forEach(([i, j], k) => {
      const a = NODES[i].pos, b = NODES[j].pos;
      restLen[k] = Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
      pos.set([a[0], a[1], a[2], b[0], b[1], b[2]], k * 6);
    });
    return { pairs, restLen, pos };
  }, []);
  const edgeRef = useRef<THREE.LineSegments>(null);

  // micro-node field with a cursor spring simulation (rest / current / velocity)
  const MICRO = 520;
  const micro = useMemo(() => {
    const rest = new Float32Array(MICRO * 3);
    const cur = new Float32Array(MICRO * 3);
    for (let i = 0; i < MICRO; i++) {
      const x = (Math.random() - 0.5) * 22;
      const y = (Math.random() - 0.5) * 12;
      const z = GRAPH_CENTER_Z + (Math.random() - 0.5) * 16;
      rest.set([x, y, z], i * 3); cur.set([x, y, z], i * 3);
    }
    return { rest, cur, vel: new Float32Array(MICRO * 3) };
  }, []);
  const microRef = useRef<THREE.Points>(null);

  // flow particles along edges
  const FLOW = 70;
  const flow = useMemo(() => ({
    pos: new Float32Array(FLOW * 3),
    meta: Array.from({ length: FLOW }, () => ({ e: Math.floor(Math.random() * EDGES.length), t: Math.random(), s: 0.05 + Math.random() * 0.12 })),
  }), []);
  const flowRef = useRef<THREE.Points>(null);

  // interaction plane sits at the graph's central depth; cursor is raycast onto it, then
  // converted into the (rotating/scaling) group's local space so forces stay accurate.
  const plane = useMemo(() => new THREE.Plane(new THREE.Vector3(0, 0, 1), -GRAPH_CENTER_Z), []);
  const ray = useMemo(() => new THREE.Raycaster(), []);
  const cursorWorld = useMemo(() => new THREE.Vector3(), []);
  const cursorLocal = useMemo(() => new THREE.Vector3(), []);
  const prevCursor = useRef(new THREE.Vector3());
  const touch = useMemo(() => typeof window !== "undefined" && !!window.matchMedia && window.matchMedia("(pointer: coarse)").matches, []);

  const setup = (mesh: THREE.InstancedMesh | null) => {
    if (!mesh) return;
    NODES.forEach((n, i) => {
      dummy.position.set(...n.pos);
      dummy.scale.setScalar((n.size ?? 0.7) * 0.28);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
      mesh.setColorAt(i, colors[i]);
    });
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  };

  useFrame((_s, dt) => {
    const p = progress.current;
    const appear = vis(p, [BAND.networkReveal[0], 1.01], 0.12); // present from reveal → end
    const on = appear > 0.01;
    if (group.current) {
      group.current.visible = on;
      group.current.rotation.y += dt * 0.015;
      group.current.scale.setScalar(0.7 + appear * 0.3);
    }
    if (!on) return;

    // cursor → world point on the network plane, then into the group's local space
    // (the group rotates + scales, so forces must be computed in the same frame).
    ray.setFromCamera(pointer as THREE.Vector2, camera);
    const hit = !touch && !!ray.ray.intersectPlane(plane, cursorWorld);
    if (hit && group.current) { cursorLocal.copy(cursorWorld); group.current.worldToLocal(cursorLocal); }
    const t = _s.clock.elapsedTime;

    // cursor speed (local space) → velocity-aware ripple, clamped so fast flicks don't explode
    let speedBoost = 0;
    if (hit) {
      speedBoost = Math.min(cursorLocal.distanceTo(prevCursor.current) / Math.max(dt, 0.001) * 0.12, 1.4);
      prevCursor.current.copy(cursorLocal);
    }

    // --- major nodes: rest spring + idle drift + cursor repulsion (subtle on Z) ---
    {
      const { rest, cur, vel, phase } = node;
      const N = NODES.length, R = 3.3, R2 = R * R;
      for (let i = 0; i < N; i++) {
        const ix = i * 3;
        // idle micro-motion even when the cursor is still
        const tx = rest[ix] + Math.sin(t * 0.5 + phase[i]) * 0.05;
        const ty = rest[ix + 1] + Math.cos(t * 0.4 + phase[i] * 1.3) * 0.05;
        const tz = rest[ix + 2] + Math.sin(t * 0.35 + phase[i] * 0.7) * 0.04;
        let fx = (tx - cur[ix]) * 0.05, fy = (ty - cur[ix + 1]) * 0.05, fz = (tz - cur[ix + 2]) * 0.05;
        if (hit) {
          const dx = cur[ix] - cursorLocal.x, dy = cur[ix + 1] - cursorLocal.y, dz = cur[ix + 2] - cursorLocal.z;
          const d2 = dx * dx + dy * dy + dz * dz;
          if (d2 < R2) {
            const d = Math.sqrt(d2) || 0.001;
            const fall = 1 - d / R;
            const f = fall * fall * (0.85 + speedBoost);
            fx += (dx / d) * f; fy += (dy / d) * f; fz += (dz / d) * f * 0.45;
          }
        }
        vel[ix] = (vel[ix] + fx) * 0.9;
        vel[ix + 1] = (vel[ix + 1] + fy) * 0.9;
        vel[ix + 2] = (vel[ix + 2] + fz) * 0.9;
      }
      // elastic links: connected nodes tug each other so ripples travel the neighborhood
      const { pairs, restLen } = edge;
      for (let k = 0; k < pairs.length; k++) {
        const i = pairs[k][0], j = pairs[k][1], a = i * 3, b = j * 3;
        const dx = cur[b] - cur[a], dy = cur[b + 1] - cur[a + 1], dz = cur[b + 2] - cur[a + 2];
        const d = Math.hypot(dx, dy, dz) || 0.001;
        const diff = ((d - restLen[k]) / d) * 0.018;
        vel[a] += dx * diff; vel[a + 1] += dy * diff; vel[a + 2] += dz * diff;
        vel[b] -= dx * diff; vel[b + 1] -= dy * diff; vel[b + 2] -= dz * diff;
      }
      for (let i = 0; i < N * 3; i++) cur[i] += vel[i];
    }

    // micro-node spring physics (cursor force-field, larger radius / lighter force)
    {
      const { rest, cur, vel } = micro;
      const R = 3.8, R2 = R * R;
      for (let i = 0; i < MICRO; i++) {
        const ix = i * 3;
        let fx = (rest[ix] - cur[ix]) * 0.05;
        let fy = (rest[ix + 1] - cur[ix + 1]) * 0.05;
        let fz = (rest[ix + 2] - cur[ix + 2]) * 0.05;
        if (hit) {
          const dx = cur[ix] - cursorLocal.x, dy = cur[ix + 1] - cursorLocal.y, dz = cur[ix + 2] - cursorLocal.z;
          const d2 = dx * dx + dy * dy + dz * dz;
          if (d2 < R2) {
            const d = Math.sqrt(d2) || 0.001;
            const f = (1 - d / R) * (0.4 + speedBoost * 0.5);
            fx += (dx / d) * f; fy += (dy / d) * f; fz += (dz / d) * f * 0.5;
          }
        }
        vel[ix] = (vel[ix] + fx) * 0.88;
        vel[ix + 1] = (vel[ix + 1] + fy) * 0.88;
        vel[ix + 2] = (vel[ix + 2] + fz) * 0.88;
        cur[ix] += vel[ix]; cur[ix + 1] += vel[ix + 1]; cur[ix + 2] += vel[ix + 2];
      }
      if (microRef.current) (microRef.current.geometry.attributes.position as THREE.BufferAttribute).needsUpdate = true;
    }

    // major-node instances follow the physics; hovered node gets a scale bump (secondary)
    if (inst.current) {
      const { cur } = node;
      const h = hovered.current;
      for (let i = 0; i < NODES.length; i++) {
        const ix = i * 3;
        dummy.position.set(cur[ix], cur[ix + 1], cur[ix + 2]);
        const base = (NODES[i].size ?? 0.7) * 0.28;
        dummy.scale.setScalar(i === h ? base * 1.7 : base);
        dummy.updateMatrix();
        inst.current.setMatrixAt(i, dummy.matrix);
      }
      inst.current.instanceMatrix.needsUpdate = true;
    }

    // edges follow the displaced node endpoints
    if (edgeRef.current) {
      const arr = (edgeRef.current.geometry.attributes.position as THREE.BufferAttribute).array as Float32Array;
      const { cur } = node;
      const { pairs } = edge;
      for (let k = 0; k < pairs.length; k++) {
        const a = pairs[k][0] * 3, b = pairs[k][1] * 3, o = k * 6;
        arr[o] = cur[a]; arr[o + 1] = cur[a + 1]; arr[o + 2] = cur[a + 2];
        arr[o + 3] = cur[b]; arr[o + 4] = cur[b + 1]; arr[o + 5] = cur[b + 2];
      }
      (edgeRef.current.geometry.attributes.position as THREE.BufferAttribute).needsUpdate = true;
    }

    // flow particles ride the (now moving) edges
    {
      const arr = flow.pos, { cur } = node;
      for (let k = 0; k < FLOW; k++) {
        const m = flow.meta[k];
        m.t += m.s * dt;
        if (m.t > 1) { m.t = 0; m.e = Math.floor(Math.random() * EDGES.length); }
        const ia = NODE_INDEX[EDGES[m.e][0]] * 3, ib = NODE_INDEX[EDGES[m.e][1]] * 3;
        arr[k * 3] = THREE.MathUtils.lerp(cur[ia], cur[ib], m.t);
        arr[k * 3 + 1] = THREE.MathUtils.lerp(cur[ia + 1], cur[ib + 1], m.t);
        arr[k * 3 + 2] = THREE.MathUtils.lerp(cur[ia + 2], cur[ib + 2], m.t);
      }
      if (flowRef.current) (flowRef.current.geometry.attributes.position as THREE.BufferAttribute).needsUpdate = true;
    }
  });

  const handleMove = (e: { instanceId?: number }) => {
    const id = e.instanceId ?? null;
    hovered.current = id;
    const nodeId = id != null ? NODES[id].id : null;
    if (nodeId !== lastReported.current) { lastReported.current = nodeId; onHover(nodeId); }
  };
  const handleOut = () => { hovered.current = null; if (lastReported.current) { lastReported.current = null; onHover(null); } };

  return (
    <group ref={group} visible={false}>
      <points ref={microRef}>
        <bufferGeometry><bufferAttribute attach="attributes-position" args={[micro.cur, 3]} /></bufferGeometry>
        <pointsMaterial color="#4a5a7a" size={0.06} transparent opacity={0.7} depthWrite={false} sizeAttenuation />
      </points>
      <lineSegments ref={edgeRef}>
        <bufferGeometry><bufferAttribute attach="attributes-position" args={[edge.pos, 3]} /></bufferGeometry>
        <lineBasicMaterial color="#2b3550" transparent opacity={0.4} />
      </lineSegments>
      <points ref={flowRef}>
        <bufferGeometry><bufferAttribute attach="attributes-position" args={[flow.pos, 3]} /></bufferGeometry>
        <pointsMaterial color="#9ecbff" size={0.11} transparent opacity={0.95} depthWrite={false} />
      </points>
      <instancedMesh
        ref={(m) => { inst.current = m; setup(m); }}
        args={[undefined as unknown as THREE.BufferGeometry, undefined as unknown as THREE.Material, NODES.length]}
        onPointerMove={handleMove}
        onPointerOut={handleOut}
      >
        <icosahedronGeometry args={[1, 1]} />
        <meshStandardMaterial emissive="#20304a" emissiveIntensity={0.4} roughness={0.4} metalness={0.15} toneMapped={false} />
      </instancedMesh>
    </group>
  );
}

// camera keyframes anchored to band midpoints
const mid = (id: keyof typeof BAND) => (BAND[id][0] + BAND[id][1]) / 2;
type Key = { p: number; pos: [number, number, number]; look: [number, number, number] };
const KEYS: Key[] = [
  { p: 0, pos: [0, 0, 9], look: [0, 0.3, 0] },
  { p: mid("hero"), pos: [0, 0, 9], look: [0, 0.3, 0] },
  { p: mid("researcher"), pos: [-1.4, 0.1, 5], look: [-1.6, 0.1, 0] },
  { p: mid("planner"), pos: [1.4, 0.3, 5], look: [1.5, 0.3, 0] },
  { p: mid("coder"), pos: [-1.4, 0.1, 5], look: [-1.5, 0.1, 0] },
  { p: mid("analyst"), pos: [0, -0.1, 5], look: [0.1, -0.2, 0] },
  { p: mid("team"), pos: [0, 0.3, 8], look: [0, -0.2, -1] },
  { p: mid("words"), pos: [0, 0, 6.5], look: [0, 0, -2] },
  { p: mid("comms"), pos: [0, 0.4, 8], look: [0, -0.2, -1] },
  { p: mid("networkReveal"), pos: [0, 1.0, 11], look: [0, 0, GRAPH_CENTER_Z] },
  { p: mid("networkExplore"), pos: [0, 0.6, 9.5], look: [0, 0, GRAPH_CENTER_Z] },
  { p: mid("payoff"), pos: [0, 3, 21], look: [0, 0, GRAPH_CENTER_Z] },
  { p: 1, pos: [0, 3.4, 24], look: [0, 0, GRAPH_CENTER_Z] },
];

function Rig({ progress, debug }: { progress: Progress; debug: DebugRef }) {
  const { camera, pointer } = useThree();
  const pos = useMemo(() => new THREE.Vector3(0, 0, 9), []);
  const look = useMemo(() => new THREE.Vector3(), []);
  const curLook = useRef(new THREE.Vector3(0, 0.3, 0));
  useFrame(() => {
    const p = progress.current;
    if (debug) debug.current.camZ = Math.round(camera.position.z * 10) / 10;
    let i = 0; while (i < KEYS.length - 1 && p > KEYS[i + 1].p) i++;
    const a = KEYS[i], b = KEYS[Math.min(i + 1, KEYS.length - 1)];
    const t = THREE.MathUtils.clamp((p - a.p) / ((b.p - a.p) || 1), 0, 1);
    const e = t * t * (3 - 2 * t);
    pos.set(THREE.MathUtils.lerp(a.pos[0], b.pos[0], e), THREE.MathUtils.lerp(a.pos[1], b.pos[1], e), THREE.MathUtils.lerp(a.pos[2], b.pos[2], e));
    look.set(THREE.MathUtils.lerp(a.look[0], b.look[0], e), THREE.MathUtils.lerp(a.look[1], b.look[1], e), THREE.MathUtils.lerp(a.look[2], b.look[2], e));
    // reduce cursor parallax while exploring the network (cursor drives nodes there)
    const explore = vis(p, BAND.networkExplore, 0.2);
    const par = 0.5 * (1 - explore);
    camera.position.x += (pos.x + pointer.x * par - camera.position.x) * 0.06;
    camera.position.y += (pos.y + pointer.y * par * 0.7 - camera.position.y) * 0.06;
    camera.position.z += (pos.z - camera.position.z) * 0.06;
    curLook.current.lerp(look, 0.08);
    camera.lookAt(curLook.current);
  });
  return null;
}

export default function AgentWorld({ progress, onHover, debug }: { progress: Progress; onHover: HoverCb; debug?: DebugRef }) {
  return (
    <Canvas
      className="xp-canvas"
      dpr={[1, 1.8]}
      gl={{ antialias: true, powerPreference: "high-performance", alpha: true }}
      camera={{ position: [0, 0, 9], fov: 55 }}
    >
      <fog attach="fog" args={["#07090B", 14, 52]} />
      <ambientLight intensity={0.6} />
      <pointLight position={[6, 6, 6]} intensity={45} color="#6EA8FF" />
      <pointLight position={[-6, -3, 2]} intensity={28} color="#8B7DF6" />
      <Stars radius={100} depth={70} count={2400} factor={3} saturation={0} fade speed={0.4} />
      <Suspense fallback={null}><Mascots progress={progress} debug={debug} /></Suspense>
      <Network progress={progress} onHover={onHover} />
      <Rig progress={progress} debug={debug} />
    </Canvas>
  );
}
