"use client";

// The persistent agent-universe canvas (World 1). One R3F <Canvas> behind the HTML
// scenes: drifting starfield, a few glowing "agent nodes" connected by faint links,
// cursor parallax, and a scroll-driven camera dolly. Scroll progress is read from a
// ref every frame (never React state) so scrolling stays 60fps.

import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Float, Line, Stars } from "@react-three/drei";
import { useMemo, useRef, type MutableRefObject } from "react";
import * as THREE from "three";

type Progress = MutableRefObject<number>;

const NODES: { pos: [number, number, number]; color: string; scale: number }[] = [
  { pos: [-3.2, 1.4, -2], color: "#6EA8FF", scale: 0.5 },
  { pos: [3.0, 0.6, -3], color: "#4ADE80", scale: 0.42 },
  { pos: [1.4, -1.6, -1.5], color: "#F5C542", scale: 0.36 },
  { pos: [-2.2, -1.2, -4], color: "#8B7DF6", scale: 0.46 },
  { pos: [0.4, 2.1, -5], color: "#6EA8FF", scale: 0.4 },
];

function AgentNode({ pos, color, scale }: (typeof NODES)[number]) {
  return (
    <Float speed={1.4} rotationIntensity={0.3} floatIntensity={0.8}>
      <mesh position={pos} scale={scale}>
        <icosahedronGeometry args={[1, 1]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.9} roughness={0.35} metalness={0.1} />
      </mesh>
    </Float>
  );
}

function Links() {
  const pairs = useMemo(
    () => [
      [NODES[0].pos, NODES[4].pos],
      [NODES[0].pos, NODES[3].pos],
      [NODES[1].pos, NODES[2].pos],
      [NODES[4].pos, NODES[1].pos],
    ] as [number[], number[]][],
    [],
  );
  return (
    <>
      {pairs.map((p, i) => (
        <Line key={i} points={[p[0] as [number, number, number], p[1] as [number, number, number]]} color="#2b3550" lineWidth={1} transparent opacity={0.5} />
      ))}
    </>
  );
}

function Rig({ progress }: { progress: Progress }) {
  const { camera, pointer } = useThree();
  const group = useRef<THREE.Group>(null);
  useFrame(() => {
    // scroll dolly: travel forward through the world as the page scrolls
    const p = progress.current;
    const targetZ = 8 - p * 6;
    camera.position.z += (targetZ - camera.position.z) * 0.05;
    camera.position.y += (p * -1.5 - camera.position.y) * 0.05;
    // cursor parallax (subtle)
    if (group.current) {
      group.current.rotation.y += (pointer.x * 0.18 - group.current.rotation.y) * 0.04;
      group.current.rotation.x += (-pointer.y * 0.12 - group.current.rotation.x) * 0.04;
    }
  });
  return (
    <group ref={group}>
      <ambientLight intensity={0.5} />
      <pointLight position={[6, 6, 6]} intensity={40} color="#6EA8FF" />
      <pointLight position={[-6, -3, 2]} intensity={25} color="#8B7DF6" />
      <Stars radius={60} depth={40} count={1600} factor={3} saturation={0} fade speed={0.6} />
      <Links />
      {NODES.map((n, i) => <AgentNode key={i} {...n} />)}
    </group>
  );
}

export default function AgentWorld({ progress }: { progress: Progress }) {
  return (
    <Canvas
      className="xp-canvas"
      dpr={[1, 1.8]}
      gl={{ antialias: true, powerPreference: "high-performance", alpha: true }}
      camera={{ position: [0, 0, 8], fov: 55 }}
    >
      <Rig progress={progress} />
    </Canvas>
  );
}
