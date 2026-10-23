import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig, Easing} from 'remotion';
import {Caption, Flash, Finish, FONT, PALETTE, Progress, TitleCard} from './ui';

// A "system diagram" style explainer: nodes pop in, edges draw themselves, packets travel, one kinetic-type slam.
type Node = {id: string; label: string; x: number; y: number; at: number; icon: string; color: string};
const NODES: Node[] = [
  {id: 'browser', label: 'Your browser', x: 540, y: 520, at: 80, icon: '🖥', color: PALETTE.cyan},
  {id: 'api', label: 'API server', x: 540, y: 900, at: 110, icon: '⚙️', color: PALETTE.ink},
  {id: 'auth', label: 'Auth service', x: 270, y: 1260, at: 140, icon: '🔐', color: PALETTE.accent},
  {id: 'db', label: 'Database', x: 810, y: 1260, at: 170, icon: '🗄', color: PALETTE.pink},
];
const EDGES: [string, string, number][] = [['browser', 'api', 100], ['api', 'auth', 130], ['api', 'db', 160]];
const byId = Object.fromEntries(NODES.map((n) => [n.id, n]));

const NodeView: React.FC<{n: Node}> = ({n}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: frame - n.at, fps, config: {damping: 10, stiffness: 170}});
  const active = frame > n.at + 40 ? 1 : 0;
  return (
    <div style={{position: 'absolute', left: n.x - 150, top: n.y - 90, width: 300, height: 180, transform: `scale(${s})`, opacity: s, borderRadius: 32, background: 'rgba(255,255,255,0.05)', border: `3px solid ${n.color}`, boxShadow: `0 0 ${30 + active * 20}px ${n.color}55, inset 0 0 40px rgba(255,255,255,0.03)`, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', fontFamily: FONT, color: PALETTE.ink}}>
      <div style={{fontSize: 64, lineHeight: 1}}>{n.icon}</div>
      <div style={{fontSize: 34, fontWeight: 800, marginTop: 12}}>{n.label}</div>
    </div>
  );
};

// Draw an edge with stroke-dashoffset; return path helpers for packets.
const EdgeView: React.FC<{a: Node; b: Node; at: number}> = ({a, b, at}) => {
  const frame = useCurrentFrame();
  const d = interpolate(frame, [at, at + 30], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const len = Math.hypot(b.x - a.x, b.y - a.y);
  return (
    <svg style={{position: 'absolute', inset: 0}} width={1080} height={1920}>
      <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="rgba(255,255,255,0.25)" strokeWidth={6} strokeLinecap="round" strokeDasharray={len} strokeDashoffset={d * len} />
    </svg>
  );
};

// Packet traveling from a to b between frames [f0, f1], with a label.
const PacketView: React.FC<{from: string; to: string; f0: number; f1: number; label: string; color: string}> = ({from, to, f0, f1, label, color}) => {
  const frame = useCurrentFrame();
  if (frame < f0 || frame > f1 + 6) return null;
  const a = byId[from], b = byId[to];
  const t = interpolate(frame, [f0, f1], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)});
  const x = a.x + (b.x - a.x) * t, y = a.y + (b.y - a.y) * t;
  const fade = interpolate(frame, [f1, f1 + 6], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <div style={{position: 'absolute', left: x, top: y, transform: 'translate(-50%,-50%)', opacity: fade}}>
      <div style={{width: 34, height: 34, borderRadius: 17, background: color, boxShadow: `0 0 30px ${color}, 0 0 60px ${color}88`, margin: '0 auto'}} />
      <div style={{marginTop: 10, padding: '8px 18px', borderRadius: 14, background: '#0b0f1a', border: `2px solid ${color}`, color, fontFamily: '"DejaVu Sans Mono", monospace', fontWeight: 700, fontSize: 28, whiteSpace: 'nowrap'}}>{label}</div>
    </div>
  );
};

// Kinetic typography slam: a single word that punches in huge, then settles.
const Slam: React.FC<{word: string; at: number; hold: number; color: string}> = ({word, at, hold, color}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (frame < at || frame > at + hold) return null;
  const s = spring({frame: frame - at, fps, config: {damping: 8, stiffness: 300, mass: 0.6}});
  const shake = frame - at < 6 ? (Math.random() - 0.5) * 0 : 0; // deterministic: keep 0, shake comes from spring overshoot
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
      <div style={{transform: `scale(${0.4 + s * 0.8}) rotate(${(1 - s) * 6 + shake}deg)`, fontFamily: FONT, fontWeight: 900, fontSize: 260, letterSpacing: -14, color, textShadow: `0 0 60px ${color}99`}}>{word}</div>
    </AbsoluteFill>
  );
};

export const Explainer2D: React.FC = () => {
  const frame = useCurrentFrame();
  const dim = frame >= 330 && frame <= 400 ? 0.15 : 1; // dim diagram during the slam
  return (
    <AbsoluteFill style={{backgroundColor: PALETTE.bg, fontFamily: FONT}}>
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 20%, #182046 0%, #0b0f1a 60%)'}} />
      <AbsoluteFill style={{opacity: 0.25, backgroundImage: 'radial-gradient(rgba(255,255,255,.18) 1.5px, transparent 1.5px)', backgroundSize: '48px 48px'}} />
      <TitleCard text="What happens when|you press Login?" start={0} end={70} sub="in 20 seconds" />
      <Flash at={70} />
      <AbsoluteFill style={{opacity: dim}}>
        {EDGES.map(([a, b, at]) => <EdgeView key={a + b} a={byId[a]} b={byId[b]} at={at} />)}
        {NODES.map((n) => <NodeView key={n.id} n={n} />)}
        <PacketView from="browser" to="api" f0={190} f1={225} label="POST /login" color={PALETTE.cyan} />
        <PacketView from="api" to="auth" f0={235} f1={265} label="hash(password)" color={PALETTE.accent} />
        <PacketView from="auth" to="db" f0={270} f1={300} label="compare hash" color={PALETTE.pink} />
        <PacketView from="db" to="api" f0={410} f1={440} label="✓ match" color={PALETTE.pink} />
        <PacketView from="api" to="browser" f0={445} f1={480} label="token: eyJ…" color={PALETTE.accent} />
      </AbsoluteFill>
      <Caption words="Your password leaves the browser once, over HTTPS." start={74} end={228} highlight={['once']} />
      <Caption words="The server hashes it. One-way. It can't be reversed." start={232} end={318} highlight={['hashes', 'One-way']} />
      <Caption words="Your real password is" start={322} end={400} y={1420} />
      <Slam word="NEVER" at={332} hold={70} color={PALETTE.pink} />
      <Caption words="stored. Only the hash is compared." start={402} end={444} highlight={['hash']} />
      <Caption words="If it matches, you get a signed token for the next requests." start={446} end={528} highlight={['signed', 'token']} />
      <Flash at={530} color={PALETTE.accent} />
      <TitleCard text="Hash, compare,|hand out a token." start={530} end={600} sub="that's login" />
      <Finish />
      <Progress />
    </AbsoluteFill>
  );
};
