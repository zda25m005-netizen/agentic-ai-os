"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { Environment, Lightformer, Line, RoundedBox } from "@react-three/drei";
import { Suspense, useMemo, useRef } from "react";
import * as THREE from "three";

const colors = ["#7ea8ef", "#e9bc64", "#7abfa9", "#ac8acb"];
const positions = [[1, -.2, 0], [-1.35, -.6, -.5], [-.65, 1.65, -1], [-.4, -2.05, -1]];

function Companion({ index, active, motion }: { index: number; active: number; motion: boolean }) {
  const root = useRef<THREE.Group>(null);
  const face = useRef<THREE.Group>(null);
  const hand = useRef<THREE.Mesh>(null);
  const shape = useMemo(() => {
    const s = new THREE.Shape();
    if (index === 2) {
      s.moveTo(0, 1.12); s.quadraticCurveTo(.15, 1.2, .35, .86);
      s.lineTo(1, -.55); s.quadraticCurveTo(1.25, -.95, .72, -1);
      s.lineTo(-.72, -1); s.quadraticCurveTo(-1.25, -.95, -1, -.55);
      s.lineTo(-.25, .92); s.quadraticCurveTo(-.12, 1.15, 0, 1.12);
    } else {
      s.moveTo(.3, 1.2); s.bezierCurveTo(-1.6, 1.2, -1.6, -1.2, .3, -1.2);
      s.bezierCurveTo(-.65, -.5, -.65, .5, .3, 1.2);
    }
    return s;
  }, [index]);
  useFrame(({ clock, pointer }, delta) => {
    if (!root.current) return;
    const t = motion ? clock.elapsedTime : 0;
    const focused = active === index;
    const group = active < 0 || active === 4;
    const p = positions[index];
    const x = group ? p[0] : focused ? .15 : p[0] * 1.7;
    const y = group ? p[1] : focused ? 0 : -8;
    const z = group ? p[2] : focused ? 1 : -5;
    const lerp = motion ? 1 - Math.exp(-delta * 4) : 1;
    root.current.position.lerp(new THREE.Vector3(x, y + Math.sin(t * .65 + index * 1.5) * .13, z), lerp);
    const scale = group ? (index === 0 ? .8 : .55) : focused ? 1.05 : .3;
    root.current.scale.lerp(new THREE.Vector3(scale, scale, scale), lerp);
    root.current.rotation.y = motion ? Math.sin(t * .3 + index) * .13 + pointer.x * .14 : -.1;
    root.current.rotation.z = Math.sin(t * .4 + index) * .06;
    if (face.current) { face.current.position.x = motion ? pointer.x * .05 : 0; face.current.position.y = motion ? pointer.y * .04 : 0; }
    if (hand.current) { hand.current.position.y = .05 + Math.sin(t * 1.5) * .12; hand.current.rotation.z = Math.sin(t * 2) * .3; }
  });
  const shell = <meshPhysicalMaterial color={colors[index]} roughness={.24} metalness={.18} clearcoat={1} clearcoatRoughness={.17} />;
  return <group ref={root} position={positions[index] as [number, number, number]}>
    {index === 0 && <RoundedBox args={[2.1, 1.85, 1.12]} radius={.4} smoothness={6}>{shell}</RoundedBox>}
    {index === 1 && <mesh scale={[.9, 1.15, .7]}><sphereGeometry args={[1, 48, 32]} />{shell}</mesh>}
    {index >= 2 && <mesh position={[index === 3 ? .35 : 0, 0, -.3]}><extrudeGeometry args={[shape, { depth: .55, bevelEnabled: true, bevelSegments: 5, steps: 1, bevelSize: .13, bevelThickness: .13, curveSegments: 36 }]} />{shell}</mesh>}
    <group ref={face}>
      <RoundedBox args={[index === 3 ? .78 : 1.48, index === 2 ? .91 : 1.15, .23]} radius={.28} smoothness={5} position={[index === 3 ? -.23 : 0, index === 2 ? -.2 : 0, .58]}><meshPhysicalMaterial color="#101d27" metalness={.4} roughness={.15} clearcoat={1} /></RoundedBox>
      {[-1, 1].map(side => <group key={side} position={[(index === 3 ? -.23 : 0) + side * (index === 3 ? .18 : .34), index === 2 ? -.12 : .1, .715]}>
        <mesh scale={[.115, .155, .06]}><sphereGeometry args={[1, 24, 16]} /><meshStandardMaterial color="#effffb" emissive="#c7efec" emissiveIntensity={.8} /></mesh>
        <mesh position={[.02, .01, .052]} scale={[.051, .073, .023]}><sphereGeometry args={[1, 16, 12]} /><meshBasicMaterial color="#172c38" /></mesh>
      </group>)}
      <mesh position={[index === 3 ? -.23 : 0, index === 2 ? -.32 : -.13, .721]} rotation={[0, 0, Math.PI]}><torusGeometry args={[.13, .025, 8, 24, Math.PI]} /><meshStandardMaterial color="#d1fff5" emissive="#99e7db" emissiveIntensity={.7} /></mesh>
    </group>
    {index !== 3 && <>
      <mesh position={[-1.25, -.4, .15]} scale={[.22, .3, .25]}><sphereGeometry args={[1, 24, 16]} />{shell}</mesh>
      <mesh ref={hand} position={[1.3, .12, .15]} scale={[.23, .32, .25]}><sphereGeometry args={[1, 24, 16]} />{shell}</mesh>
    </>}
    <mesh position={[index === 3 ? .55 : .15, 1.48, 0]}><sphereGeometry args={[.1, 20, 16]} /><meshStandardMaterial color={colors[index]} emissive={colors[index]} emissiveIntensity={1.7} /></mesh>
    {index === 1 && <group position={[-1.1, -.35, .8]} rotation={[.1, -.3, -.25]}><RoundedBox args={[.46, .64, .025]} radius={.03}><meshStandardMaterial color="#efe4cc" /></RoundedBox>{[0, 1, 2].map(i => <mesh key={i} position={[0, .13 - i * .13, .02]}><boxGeometry args={[.28, .018, .012]} /><meshBasicMaterial color="#9e8c66" /></mesh>)}</group>}
    {index === 2 && <mesh position={[1.28, .65, .3]} rotation={[.2, -.4, .3]}><torusGeometry args={[.27, .05, 12, 40]} />{shell}</mesh>}
    {index === 3 && <mesh position={[.65, -.55, .1]}><sphereGeometry args={[.16, 24, 16]} /><meshPhysicalMaterial color="#eee2fd" roughness={.15} metalness={.5} /></mesh>}
  </group>;
}

function Orbits({ motion }: { motion: boolean }) {
  const ref = useRef<THREE.Group>(null);
  const paths = useMemo(() => [0, 1, 2].map(k => Array.from({ length: 129 }, (_, i) => {
    const t = i / 128 * Math.PI * 2;
    return new THREE.Vector3(Math.cos(t) * (4.3 + k * .7), Math.sin(t) * (1.5 + k * .3), Math.sin(t) * 2 - 2);
  })), []);
  const particles = useMemo(() => {
    const arr = new Float32Array(210 * 3);
    for (let i = 0; i < 210; i++) { arr[i * 3] = Math.sin(i * 127.1) * 10; arr[i * 3 + 1] = Math.cos(i * 73.7) * 7; arr[i * 3 + 2] = -3 - (i % 19) * .45; }
    return arr;
  }, []);
  useFrame(({ clock }) => { if (ref.current && motion) ref.current.rotation.z = .2 + Math.sin(clock.elapsedTime * .06) * .07; });
  return <group ref={ref} rotation={[0, 0, .2]}>
    {paths.map((points, i) => <Line key={i} points={points} color="#a2a7b5" transparent opacity={.14 - i * .025} lineWidth={.6} />)}
    <points><bufferGeometry><bufferAttribute attach="attributes-position" args={[particles, 3]} /></bufferGeometry><pointsMaterial color="#d5c7b3" size={.023} transparent opacity={.55} sizeAttenuation /></points>
  </group>;
}

export default function Scene({ active, motion }: { active: number; motion: boolean }) {
  return <Canvas dpr={[1, 1.5]} camera={{ position: [0, .2, 10], fov: 43 }} gl={{ alpha: true, antialias: true }} aria-label="Interactive 3D agent observatory">
    <ambientLight intensity={.8} />
    <directionalLight position={[-3, 5, 6]} intensity={3} color="#fff0da" />
    <directionalLight position={[4, 0, 3]} intensity={2.5} color="#a8c8ff" />
    <Suspense fallback={null}>
      <Environment resolution={128}><Lightformer position={[0, 5, -4]} scale={[10, 4, 1]} intensity={3} color="#b4caff" /><Lightformer position={[-5, 2, 2]} rotation={[0, Math.PI / 2, 0]} scale={[3, 8, 1]} intensity={4} color="#ffe7be" /></Environment>
      <Orbits motion={motion} />
      {[0, 1, 2, 3].map(index => <Companion key={index} index={index} active={active} motion={motion} />)}
    </Suspense>
  </Canvas>;
}
