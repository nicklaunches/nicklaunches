import React, {useMemo} from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig, Easing} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import * as THREE from 'three';
import {RoundedBoxGeometry} from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import {Caption, Counter, Flash, Finish, PALETTE, Progress, TitleCard} from './ui';

// ---------- timeline (frames @30fps) ----------
const T = {
  hookEnd: 75, slowStart: 95, slowEnd: 235, edgesIn: 250, fastStart: 310, fastEnd: 430, cacheStart: 470, cacheEnd: 600, payoff: 620,
};
const USER = new THREE.Vector3(0, 0.45, 4.2);
const ORIGIN = new THREE.Vector3(0, 1.4, -13);
const EDGES: THREE.Vector3[] = [
  new THREE.Vector3(-2.6, 0.5, 1.2), new THREE.Vector3(2.9, 0.5, 0.6), new THREE.Vector3(-3.4, 0.5, -3.2),
  new THREE.Vector3(3.6, 0.5, -3.8), new THREE.Vector3(0.4, 0.5, -6.5),
];
const NEAREST = EDGES[0];

// Clay / vinyl-toy material: no metal, mid roughness, light clearcoat.
const clay = (color: string, emissive = '#000000', ei = 0) => (
  <meshPhysicalMaterial color={color} roughness={0.45} metalness={0} clearcoat={0.35} clearcoatRoughness={0.4} emissive={emissive} emissiveIntensity={ei} />
);

const Box: React.FC<{pos: THREE.Vector3; size: [number, number, number]; color: string; scale?: number; emissive?: string; ei?: number; radius?: number}> = ({pos, size, color, scale = 1, emissive, ei, radius = 0.12}) => {
  const geo = useMemo(() => new RoundedBoxGeometry(size[0], size[1], size[2], 4, radius), [size, radius]);
  return (
    <mesh geometry={geo} position={[pos.x, pos.y, pos.z]} scale={scale} castShadow receiveShadow>
      {clay(color, emissive, ei)}
    </mesh>
  );
};

// Glowing packet = emissive sphere + soft additive halo sprite.
const haloTex = (() => {
  if (typeof document === 'undefined') return null;
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const g = c.getContext('2d')!; const r = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  r.addColorStop(0, 'rgba(255,255,255,1)'); r.addColorStop(0.3, 'rgba(255,255,255,.5)'); r.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = r; g.fillRect(0, 0, 128, 128);
  const t = new THREE.CanvasTexture(c); return t;
})();
const Packet: React.FC<{p: THREE.Vector3; color: string; r?: number}> = ({p, color, r = 0.16}) => (
  <group position={[p.x, p.y, p.z]}>
    <mesh><sphereGeometry args={[r, 24, 24]} /><meshStandardMaterial color={color} emissive={color} emissiveIntensity={2.2} roughness={0.3} /></mesh>
    {haloTex ? <sprite scale={[r * 9, r * 9, 1]}><spriteMaterial map={haloTex} color={color} transparent opacity={0.55} blending={THREE.AdditiveBlending} depthWrite={false} /></sprite> : null}
    <pointLight color={color} intensity={6} distance={5} decay={2} />
  </group>
);

// Arc path between two points (lifts the packet so the route reads in 3D).
const arc = (a: THREE.Vector3, b: THREE.Vector3, t: number, lift = 1.6) => {
  const p = new THREE.Vector3().lerpVectors(a, b, t);
  p.y += Math.sin(t * Math.PI) * lift;
  return p;
};
// Ping-pong along a path: 0..1 go, 1..2 return.
const pingPong = (a: THREE.Vector3, b: THREE.Vector3, u: number, lift?: number) => (u <= 1 ? arc(a, b, u, lift) : arc(b, a, u - 1, lift));

const Scene: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const {camera} = useThree();

  // ---- camera: hook push-in -> wide reveal -> slow orbit -> pull back on payoff
  const hook = interpolate(frame, [0, T.hookEnd], [0, 1], {extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)});
  const reveal = interpolate(frame, [T.hookEnd, T.hookEnd + 40], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const orbit = interpolate(frame, [T.hookEnd, T.payoff], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const pull = interpolate(frame, [T.payoff, T.payoff + 60], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)});
  const ang = -0.35 + orbit * 0.7;
  const dist = 9 - hook * 3 + reveal * 9 + pull * 5;
  const height = 3.5 - hook * 1.5 + reveal * 6 + pull * 3;
  camera.position.set(Math.sin(ang) * dist, height, USER.z + Math.cos(ang) * dist);
  const look = new THREE.Vector3().lerpVectors(USER, new THREE.Vector3(0, 0.5, -4), reveal);
  camera.lookAt(look);
  (camera as THREE.PerspectiveCamera).fov = 34; camera.updateProjectionMatrix();

  // ---- packets
  const slowU = interpolate(frame, [T.slowStart, T.slowEnd], [0, 2], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.sin)});
  const showSlow = frame >= T.slowStart && frame <= T.slowEnd;
  const fastPackets = [0, 1, 2, 3].map((i) => {
    const f0 = T.fastStart + i * 28;
    const u = interpolate(frame, [f0, f0 + 26], [0, 2], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.sin)});
    return {show: frame >= f0 && frame <= f0 + 26, p: pingPong(USER, NEAREST, u, 0.9)};
  });
  const cachePackets = EDGES.map((e, i) => {
    const f0 = T.cacheStart + i * 14;
    const u = interpolate(frame, [f0, f0 + 50], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)});
    return {show: frame >= f0 && frame <= f0 + 50, p: arc(ORIGIN, e, u, 2.2)};
  });

  // ---- edge nodes pop in with staggered springs; light up after they are cached
  const edgeScale = (i: number) => spring({frame: frame - T.edgesIn - i * 6, fps, config: {damping: 9, stiffness: 180}});
  const cached = (i: number) => frame >= T.cacheStart + i * 14 + 50;
  const originPulse = 0.6 + 0.4 * Math.sin(frame / 6);

  return (
    <>
      <fog attach="fog" args={[PALETTE.bg, 22, 48]} />
      <hemisphereLight args={['#dfe6ff', '#1a1f33', 1.1]} />
      <pointLight position={[ORIGIN.x, ORIGIN.y + 3, ORIGIN.z + 3]} intensity={40} color={PALETTE.pink} distance={14} decay={2} />
      <directionalLight position={[-6, 10, 6]} intensity={3.2} castShadow shadow-mapSize-width={2048} shadow-mapSize-height={2048} shadow-camera-left={-14} shadow-camera-right={14} shadow-camera-top={14} shadow-camera-bottom={-14} shadow-bias={-0.0004} />
      <directionalLight position={[8, 4, -2]} intensity={0.6} color="#9fb4ff" />
      <directionalLight position={[0, 5, -16]} intensity={1.6} color={PALETTE.cyan} />

      {/* floor + grid */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, -4]} receiveShadow>
        <planeGeometry args={[80, 80]} /><meshStandardMaterial color="#182036" roughness={0.9} />
      </mesh>
      <gridHelper args={[80, 80, '#243052', '#1a2340']} position={[0, 0, -4]} />

      {/* the user's phone */}
      <group position={[USER.x, 0, USER.z]}>
        <Box pos={new THREE.Vector3(0, 0.45, 0)} size={[0.55, 1.1, 0.08]} color="#1e2538" radius={0.06} />
        <mesh position={[0, 0.45, 0.045]}><planeGeometry args={[0.47, 1.0]} /><meshStandardMaterial color={PALETTE.cyan} emissive={PALETTE.cyan} emissiveIntensity={0.8 + 0.4 * hook} /></mesh>
      </group>

      {/* far-away origin server */}
      <group>
        <Box pos={ORIGIN} size={[1.6, 2.8, 1.6]} color="#3a4068" radius={0.15} />
        {[0.6, 0, -0.6].map((dy, i) => (
          <mesh key={i} position={[ORIGIN.x, ORIGIN.y + dy, ORIGIN.z + 0.81]}><planeGeometry args={[1.2, 0.12]} /><meshStandardMaterial color={PALETTE.pink} emissive={PALETTE.pink} emissiveIntensity={originPulse * (i === 1 ? 2 : 1)} /></mesh>
        ))}
      </group>

      {/* edge nodes */}
      {EDGES.map((e, i) => (
        <group key={i} scale={edgeScale(i)}>
          <Box pos={e} size={[0.9, 1.0, 0.9]} color={cached(i) ? '#2f3b2a' : '#283049'} emissive={cached(i) ? PALETTE.accent : '#000000'} ei={cached(i) ? 0.35 : 0} />
          <mesh position={[e.x, e.y + 0.52, e.z]}><cylinderGeometry args={[0.18, 0.18, 0.06, 24]} /><meshStandardMaterial color={PALETTE.accent} emissive={PALETTE.accent} emissiveIntensity={cached(i) ? 2.5 : 0.4} /></mesh>
        </group>
      ))}

      {showSlow ? <Packet p={pingPong(USER, ORIGIN, slowU, 2.4)} color={PALETTE.pink} /> : null}
      {fastPackets.map((f, i) => (f.show ? <Packet key={i} p={f.p} color={PALETTE.accent} r={0.13} /> : null))}
      {cachePackets.map((f, i) => (f.show ? <Packet key={i} p={f.p} color={PALETTE.cyan} r={0.12} /> : null))}
    </>
  );
};

export const Explainer3D: React.FC = () => {
  const {width, height} = useVideoConfig();
  return (
    <AbsoluteFill style={{backgroundColor: PALETTE.bg}}>
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 30%, #1a2342 0%, #0b0f1a 65%)'}} />
      <ThreeCanvas width={width} height={height} shadows gl={{antialias: true, toneMapping: THREE.ACESFilmicToneMapping}} camera={{fov: 34, near: 0.1, far: 80, position: [0, 3, 12]}} style={{width, height}}>
        <Scene />
      </ThreeCanvas>

      {/* 2D layer: captions, counters, cards */}
      <TitleCard text="Why does this load|in 40 ms?" start={0} end={T.hookEnd} sub="when the server is 9,000 km away" />
      <Flash at={T.hookEnd} />
      <Caption words="Your tap travels to ONE server across the ocean." start={T.hookEnd + 4} end={T.edgesIn - 4} highlight={['ONE']} />
      <Counter from={0} to={180} start={T.slowStart + 20} end={T.fastStart + 24} duration={110} unit="ms" x={60} y={210} color={PALETTE.pink} label="round trip" />
      <Flash at={T.edgesIn} color={PALETTE.accent} />
      <Caption words="A CDN drops copies of the file into 300+ cities." start={T.edgesIn + 4} end={T.fastStart + 6} highlight={['CDN', '300+']} />
      <Caption words="Now your tap only goes to the nearest one." start={T.fastStart + 10} end={T.cacheStart - 14} highlight={['nearest']} />
      <Counter from={180} to={40} start={T.fastStart + 30} end={T.payoff - 6} duration={70} unit="ms" x={60} y={210} color={PALETTE.accent} label="round trip" />
      <Caption words="The first visitor fills the cache. Everyone after is instant." start={T.cacheStart - 10} end={T.payoff - 4} highlight={['instant']} />
      <TitleCard text="Closer = faster.|That's a CDN." start={T.payoff} end={720} sub="follow for one idea per video" />
      <Finish />
      <Progress />
    </AbsoluteFill>
  );
};
