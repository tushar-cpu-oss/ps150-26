import { Component, useMemo, useRef, useState, type ReactNode } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Html, Line } from '@react-three/drei';
import * as THREE from 'three';

export interface NodeDef { id: string; label: string; pos: [number, number, number]; to?: string }
const NODES: NodeDef[] = [
  { id: 'evidence', label: 'EVIDENCE', pos: [-3, 0.2, 0], to: '/cases' },
  { id: 'sha', label: 'SHA-256', pos: [-1.9, 2, -0.5], to: '/cases' },
  { id: 'video', label: 'VIDEO', pos: [-1.7, -2, 0.3], to: '/cases' },
  { id: 'analysis', label: 'AI ANALYSIS', pos: [3, 0.2, 0.2], to: '/cases' },
  { id: 'timeline', label: 'TIMELINE', pos: [1.9, 2.1, -0.4], to: '/cases' },
  { id: 'report', label: 'REPORT', pos: [1.8, -2, 0.4], to: '/cases' },
];
const LINKS: [string, string][] = [
  ['camera', 'evidence'], ['evidence', 'sha'], ['evidence', 'video'], ['video', 'analysis'],
  ['analysis', 'timeline'], ['analysis', 'report'], ['camera', 'analysis'],
];
const CAMERA: NodeDef = { id: 'camera', label: 'CAMERA', pos: [0, 0, 0] };
const P = (id: string) => (id === 'camera' ? CAMERA : NODES.find((n) => n.id === id)!).pos;

function CameraModel() {
  const g = useRef<THREE.Group>(null);
  useFrame((s) => { if (g.current) g.current.position.y = Math.sin(s.clock.elapsedTime * 0.8) * 0.06; });
  const body = <meshStandardMaterial color="#141d28" metalness={0.7} roughness={0.35} />;
  return (
    <group ref={g}>
      <mesh><boxGeometry args={[1.5, 0.7, 0.7]} />{body}</mesh>
      <mesh position={[0.95, 0, 0]} rotation={[0, 0, Math.PI / 2]}><cylinderGeometry args={[0.32, 0.36, 0.55, 20]} />{body}</mesh>
      <mesh position={[1.24, 0, 0]} rotation={[0, 0, Math.PI / 2]}><cylinderGeometry args={[0.2, 0.2, 0.06, 20]} /><meshStandardMaterial color="#7CD4F7" emissive="#7CD4F7" emissiveIntensity={1.2} /></mesh>
      <mesh position={[-0.2, -0.55, 0]}><boxGeometry args={[0.18, 0.45, 0.18]} />{body}</mesh>
      <mesh position={[-0.2, -0.82, 0]}><boxGeometry args={[0.8, 0.08, 0.5]} />{body}</mesh>
      <mesh position={[-0.55, 0.2, 0.36]}><sphereGeometry args={[0.04, 8, 8]} /><meshBasicMaterial color="#F0616D" /></mesh>
    </group>
  );
}

function Packet({ from, to, offset }: { from: [number, number, number]; to: [number, number, number]; offset: number }) {
  const ref = useRef<THREE.Mesh>(null);
  const a = useMemo(() => new THREE.Vector3(...from), [from]);
  const b = useMemo(() => new THREE.Vector3(...to), [to]);
  useFrame((s) => { if (ref.current) ref.current.position.lerpVectors(a, b, ((s.clock.elapsedTime * 0.25 + offset) % 1)); });
  return <mesh ref={ref}><sphereGeometry args={[0.05, 8, 8]} /><meshBasicMaterial color="#E6EEF5" /></mesh>;
}

function Node({ n, onSelect }: { n: NodeDef; onSelect: (to?: string) => void }) {
  const [hover, setHover] = useState(false);
  const ref = useRef<THREE.Mesh>(null);
  useFrame((s) => { if (ref.current) { ref.current.rotation.y += 0.01; ref.current.scale.setScalar(THREE.MathUtils.lerp(ref.current.scale.x, hover ? 1.35 : 1 + Math.sin(s.clock.elapsedTime * 2 + n.pos[0]) * 0.05, 0.15)); } });
  return (
    <group position={n.pos}>
      <mesh ref={ref} onPointerOver={() => { setHover(true); document.body.style.cursor = 'pointer'; }}
        onPointerOut={() => { setHover(false); document.body.style.cursor = ''; }} onClick={() => onSelect(n.to)}>
        <octahedronGeometry args={[0.28]} />
        <meshStandardMaterial color="#0E141C" emissive="#7CD4F7" emissiveIntensity={hover ? 1.4 : 0.55} wireframe={!hover} />
      </mesh>
      <Html center position={[0, -0.6, 0]} style={{ pointerEvents: 'none' }}>
        <span className={`font-mono text-[10px] tracking-[0.16em] whitespace-nowrap ${hover ? 'text-ice' : 'text-slate-400'}`}>{n.label}</span>
      </Html>
    </group>
  );
}

function Scene({ onSelect }: { onSelect: (to?: string) => void }) {
  const g = useRef<THREE.Group>(null);
  useFrame((s) => {
    if (!g.current) return;
    g.current.rotation.y = THREE.MathUtils.lerp(g.current.rotation.y, s.pointer.x * 0.35 - 0.2, 0.04);
    g.current.rotation.x = THREE.MathUtils.lerp(g.current.rotation.x, -s.pointer.y * 0.18, 0.04);
  });
  return (
    <>
      <ambientLight intensity={0.6} />
      <pointLight position={[4, 4, 5]} intensity={40} color="#9fdcf7" />
      <group ref={g}>
        <CameraModel />
        {LINKS.map(([a, b], i) => (
          <group key={a + b}>
            <Line points={[P(a), P(b)]} color="#7CD4F7" lineWidth={0.6} transparent opacity={0.28} />
            <Packet from={P(a)} to={P(b)} offset={i * 0.17} />
          </group>
        ))}
        {NODES.map((n) => <Node key={n.id} n={n} onSelect={onSelect} />)}
      </group>
    </>
  );
}

export function Network2D({ onSelect }: { onSelect: (to?: string) => void }) {
  const c = (p: [number, number, number]) => ({ x: 320 + p[0] * 85, y: 220 - p[1] * 85 });
  return (
    <svg viewBox="0 0 640 440" className="w-full h-full" role="img" aria-label="Evidence network">
      {LINKS.map(([a, b]) => { const A = c(P(a)), B = c(P(b)); return <line key={a + b} x1={A.x} y1={A.y} x2={B.x} y2={B.y} stroke="#7CD4F7" strokeOpacity="0.3" />; })}
      <g transform={`translate(${c(CAMERA.pos).x - 34},${c(CAMERA.pos).y - 20})`}>
        <rect width="58" height="34" rx="4" fill="#141d28" stroke="#7CD4F7" strokeOpacity="0.6" />
        <rect x="58" y="8" width="16" height="18" rx="3" fill="#141d28" stroke="#7CD4F7" strokeOpacity="0.6" />
      </g>
      {NODES.map((n) => { const p = c(n.pos); return (
        <g key={n.id} transform={`translate(${p.x},${p.y})`} onClick={() => onSelect(n.to)} style={{ cursor: 'pointer' }} tabIndex={0} role="button" aria-label={n.label}
          onKeyDown={(e) => e.key === 'Enter' && onSelect(n.to)}>
          <rect x="-12" y="-12" width="24" height="24" transform="rotate(45)" fill="#0E141C" stroke="#7CD4F7" />
          <text y="30" textAnchor="middle" fontSize="10" fill="#94a3b8" fontFamily="JetBrains Mono, monospace" letterSpacing="1.5">{n.label}</text>
        </g>
      ); })}
    </svg>
  );
}

class Boundary extends Component<{ fallback: ReactNode; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? this.props.fallback : this.props.children; }
}

function canRender3D(): boolean {
  try {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return false;
    if ((navigator.hardwareConcurrency ?? 8) < 4) return false;
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl2') || c.getContext('webgl'));
  } catch { return false; }
}

export default function EvidenceNetwork({ onSelect }: { onSelect: (to?: string) => void }) {
  const [use3D, setUse3D] = useState(canRender3D);
  const fallback = <Network2D onSelect={onSelect} />;
  return (
    <div className="relative w-full h-full">
      {use3D ? (
        <Boundary fallback={fallback}>
          <Canvas dpr={[1, 1.5]} camera={{ position: [0, 0.5, 8.5], fov: 45 }} gl={{ antialias: true, powerPreference: 'high-performance' }}>
            <Scene onSelect={onSelect} />
          </Canvas>
        </Boundary>
      ) : fallback}
      <button onClick={() => setUse3D((v) => !v)} className="absolute bottom-2 right-2 text-[10px] font-mono tracking-wider text-slate-500 hover:text-ice">
        {use3D ? 'SWITCH TO 2D' : 'SWITCH TO 3D'}
      </button>
    </div>
  );
}
