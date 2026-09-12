"use client";

// The opening moment — BEFORE the hero. A dense floating cloud of soft particles that the
// cursor physically disturbs (repulsion + spring return). Built from three layers at
// different particle sizes so it reads like depth-of-field bokeh rather than flat dots.
// It fades out as the hero headline takes over; the hero itself is untouched.

import { useFrame, useThree } from "@react-three/fiber";
import { useMemo, useRef, type MutableRefObject } from "react";
import * as THREE from "three";
import { BAND, local } from "./timeline";

type Progress = MutableRefObject<number>;

const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
const smooth = (x: number) => x * x * (3 - 2 * x);

// soft round particle sprite (a blurred dot, not a hard square)
let SPRITE: THREE.CanvasTexture | null = null;
function sprite(): THREE.CanvasTexture {
  if (SPRITE) return SPRITE;
  const c = document.createElement("canvas"); c.width = c.height = 64;
  const g = c.getContext("2d")!;
  const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grad.addColorStop(0, "rgba(255,255,255,1)");
  grad.addColorStop(0.3, "rgba(255,255,255,0.6)");
  grad.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = grad; g.fillRect(0, 0, 64, 64);
  SPRITE = new THREE.CanvasTexture(c);
  return SPRITE;
}

const CLOUD_Z = -1.5;
// shared cursor state (written by the parent once per frame, read by every layer)
type Cursor = { hit: boolean; x: number; y: number; z: number; boost: number };

// one density layer — its own particles + physics, driven by the shared cursor
function Layer({ n, size, opacity, cursor, vis }: {
  n: number; size: number; opacity: number;
  cursor: MutableRefObject<Cursor>; vis: MutableRefObject<number>;
}) {
  const pts = useRef<THREE.Points>(null);
  const mat = useRef<THREE.PointsMaterial>(null);
  const d = useMemo(() => {
    const rest = new Float32Array(n * 3), cur = new Float32Array(n * 3);
    const vel = new Float32Array(n * 3), ph = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const th = Math.random() * Math.PI * 2, phi = Math.acos(2 * Math.random() - 1);
      const r = Math.pow(Math.random(), 0.42) * 3.6;        // dense core, sparse edge
      rest[i * 3] = Math.sin(phi) * Math.cos(th) * r * 1.32;
      rest[i * 3 + 1] = Math.sin(phi) * Math.sin(th) * r * 0.98;
      rest[i * 3 + 2] = Math.cos(phi) * r * 0.9;
      cur[i * 3] = rest[i * 3]; cur[i * 3 + 1] = rest[i * 3 + 1]; cur[i * 3 + 2] = rest[i * 3 + 2];
      ph[i] = Math.random() * Math.PI * 2;
    }
    return { rest, cur, vel, ph };
  }, [n]);

  useFrame((state) => {
    if (mat.current) mat.current.opacity = vis.current * opacity;
    if (vis.current <= 0.01 || !pts.current) return;
    const c = cursor.current, t = state.clock.elapsedTime;
    const { rest, cur, vel, ph } = d;
    const R = 2.4, R2 = R * R;
    for (let i = 0; i < n; i++) {
      const ix = i * 3;
      const tx = rest[ix] + Math.sin(t * 0.35 + ph[i]) * 0.06;
      const ty = rest[ix + 1] + Math.cos(t * 0.3 + ph[i] * 1.3) * 0.06;
      const tz = rest[ix + 2] + Math.sin(t * 0.25 + ph[i] * 0.7) * 0.05;
      let fx = (tx - cur[ix]) * 0.045, fy = (ty - cur[ix + 1]) * 0.045, fz = (tz - cur[ix + 2]) * 0.045;
      if (c.hit) {
        const dx = cur[ix] - c.x, dy = cur[ix + 1] - c.y, dz = cur[ix + 2] - c.z;
        const d2 = dx * dx + dy * dy + dz * dz;
        if (d2 < R2) {
          const dist = Math.sqrt(d2) || 0.001;
          const fall = 1 - dist / R;
          const f = fall * fall * (0.8 + c.boost);
          fx += (dx / dist) * f; fy += (dy / dist) * f; fz += (dz / dist) * f * 0.5;
        }
      }
      vel[ix] = (vel[ix] + fx) * 0.9;
      vel[ix + 1] = (vel[ix + 1] + fy) * 0.9;
      vel[ix + 2] = (vel[ix + 2] + fz) * 0.9;
      cur[ix] += vel[ix]; cur[ix + 1] += vel[ix + 1]; cur[ix + 2] += vel[ix + 2];
    }
    (pts.current.geometry.attributes.position as THREE.BufferAttribute).needsUpdate = true;
  });

  return (
    <points ref={pts}>
      <bufferGeometry><bufferAttribute attach="attributes-position" args={[d.cur, 3]} /></bufferGeometry>
      <pointsMaterial ref={mat} map={sprite()} color="#e6eefb" size={size} transparent opacity={0}
        sizeAttenuation depthWrite={false} blending={THREE.AdditiveBlending} toneMapped={false} />
    </points>
  );
}

export default function IntroCloud({ progress }: { progress: Progress }) {
  const { camera, pointer } = useThree();
  const grp = useRef<THREE.Group>(null);
  const cursor = useRef<Cursor>({ hit: false, x: 0, y: 0, z: 0, boost: 0 });
  const vis = useRef(0);

  const plane = useMemo(() => new THREE.Plane(new THREE.Vector3(0, 0, 1), -CLOUD_Z), []);
  const ray = useMemo(() => new THREE.Raycaster(), []);
  const world = useMemo(() => new THREE.Vector3(), []);
  const localV = useMemo(() => new THREE.Vector3(), []);
  const prev = useRef(new THREE.Vector3());
  const touch = useMemo(() => typeof window !== "undefined" && !!window.matchMedia && window.matchMedia("(pointer: coarse)").matches, []);

  useFrame((state, dt) => {
    const g = grp.current; if (!g) return;
    const p = progress.current;
    // full at page load, fading out over the last 45% of the intro band
    const lp = local(p, BAND.intro);
    const o = 1 - smooth(clamp01((lp - 0.55) / 0.45));
    vis.current = o;
    g.visible = o > 0.01 && p < BAND.hero[0] + 0.01;
    if (!g.visible) return;

    g.rotation.y += dt * 0.03;
    g.rotation.z = Math.sin(state.clock.elapsedTime * 0.08) * 0.04;

    // cursor → world point on the cloud plane → the group's local space (once per frame)
    ray.setFromCamera(pointer as THREE.Vector2, camera);
    const hit = !touch && !!ray.ray.intersectPlane(plane, world);
    const c = cursor.current;
    c.hit = hit;
    if (hit) {
      localV.copy(world); g.worldToLocal(localV);
      c.boost = Math.min(localV.distanceTo(prev.current) / Math.max(dt, 0.001) * 0.1, 1.3);
      c.x = localV.x; c.y = localV.y; c.z = localV.z;
      prev.current.copy(localV);
    } else { c.boost = 0; }
  });

  return (
    <group ref={grp} position={[0, 0.35, CLOUD_Z]}>
      <Layer n={9000} size={0.05} opacity={0.95} cursor={cursor} vis={vis} />
      <Layer n={4200} size={0.105} opacity={0.6} cursor={cursor} vis={vis} />
      <Layer n={700} size={0.34} opacity={0.22} cursor={cursor} vis={vis} />
    </group>
  );
}
