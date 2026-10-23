import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig, Easing} from 'remotion';

export const FONT = 'Inter, "Inter Display", system-ui, sans-serif';
export const PALETTE = {bg: '#0b0f1a', ink: '#f5f7ff', accent: '#c8ff3d', cyan: '#4df0ff', pink: '#ff5fa8', muted: '#8d95b3'};

// Word-by-word caption: each word pops in with a spring, timed to a start frame.
export const Caption: React.FC<{words: string; start: number; end?: number; perWord?: number; y?: number; size?: number; highlight?: string[]; color?: string}> = ({
  words, start, end = 1e9, perWord = 4, y = 1500, size = 64, highlight = [], color = PALETTE.ink,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const list = words.split(' ');
  if (frame < start || frame > end) return null;
  const out = interpolate(frame, [end - 8, end], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <div style={{position: 'absolute', left: 80, right: 80, top: y, opacity: out, transform: `translateY(${(1 - out) * -30}px)`, textAlign: 'center', fontFamily: FONT, fontWeight: 800, fontSize: size, lineHeight: 1.15, letterSpacing: -1, color, textShadow: '0 6px 30px rgba(0,0,0,.6)'}}>
      {list.map((w, i) => {
        const s = spring({frame: frame - start - i * perWord, fps, config: {damping: 12, stiffness: 220}});
        const hl = highlight.includes(w.replace(/[^a-zA-Z0-9]/g, ''));
        return (
          <span key={i} style={{display: 'inline-block', marginRight: 16, transform: `scale(${s}) translateY(${(1 - s) * 20}px)`, opacity: s, color: hl ? PALETTE.accent : undefined}}>
            {w}
          </span>
        );
      })}
    </div>
  );
};

// Big hook / payoff title card that slams in and holds.
export const TitleCard: React.FC<{text: string; start: number; end: number; accent?: string; sub?: string}> = ({text, start, end, accent, sub}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (frame < start || frame > end) return null;
  const s = spring({frame: frame - start, fps, config: {damping: 14, stiffness: 160, mass: 0.9}});
  const out = interpolate(frame, [end - 8, end], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', padding: 90, opacity: out, background: 'radial-gradient(ellipse at 50% 50%, rgba(11,15,26,.85) 30%, rgba(11,15,26,.35) 75%)'}}>
      <div style={{transform: `scale(${0.7 + 0.3 * s}) rotate(${(1 - s) * -4}deg)`, fontFamily: FONT, fontWeight: 900, fontSize: 118, lineHeight: 1.02, letterSpacing: -4, color: PALETTE.ink, textAlign: 'center'}}>
        {text.split('|').map((line, i) => <div key={i} style={{color: i === 1 ? (accent ?? PALETTE.accent) : undefined}}>{line}</div>)}
      </div>
      {sub ? <div style={{marginTop: 40, fontFamily: FONT, fontWeight: 600, fontSize: 44, color: PALETTE.muted, opacity: s}}>{sub}</div> : null}
    </AbsoluteFill>
  );
};

// Counter that ticks up/down with easing, e.g. "180 ms" -> "40 ms".
export const Counter: React.FC<{from: number; to: number; start: number; end?: number; duration: number; unit: string; x: number; y: number; color?: string; label?: string}> = ({from, to, start, end = 1e9, duration, unit, x, y, color = PALETTE.cyan, label}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  if (frame < start || frame > end) return null;
  const out = interpolate(frame, [end - 8, end], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const v = interpolate(frame, [start, start + duration], [from, to], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
  const pop = spring({frame: frame - start, fps, config: {damping: 10, stiffness: 200}});
  return (
    <div style={{position: 'absolute', left: x, top: y, opacity: out, transform: `scale(${pop})`, fontFamily: FONT, color, textAlign: 'center'}}>
      {label ? <div style={{fontSize: 30, fontWeight: 600, color: PALETTE.muted, letterSpacing: 4, textTransform: 'uppercase'}}>{label}</div> : null}
      <div style={{fontSize: 120, fontWeight: 900, letterSpacing: -4, fontVariantNumeric: 'tabular-nums', textShadow: `0 0 40px ${color}66`}}>
        {Math.round(v)}<span style={{fontSize: 56, fontWeight: 700, marginLeft: 8}}>{unit}</span>
      </div>
    </div>
  );
};

// Quick "slam" transition: white flash + scale punch at a cut.
export const Flash: React.FC<{at: number; color?: string}> = ({at, color = '#ffffff'}) => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [at, at + 2, at + 10], [0, 0.85, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{backgroundColor: color, opacity: o, pointerEvents: 'none'}} />;
};

// Soft vignette + subtle grain overlay for a "premium" finish.
export const Finish: React.FC = () => (
  <>
    <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 45%, rgba(0,0,0,.55) 100%)', pointerEvents: 'none'}} />
    <AbsoluteFill style={{opacity: 0.06, mixBlendMode: 'overlay', backgroundImage: 'url("data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'160\' height=\'160\'><filter id=\'n\'><feTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'2\'/></filter><rect width=\'160\' height=\'160\' filter=\'url(%23n)\'/></svg>")', pointerEvents: 'none'}} />
  </>
);

// Progress bar at the top like a story.
export const Progress: React.FC = () => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  return <div style={{position: 'absolute', top: 90, left: 80, right: 80, height: 6, borderRadius: 3, background: 'rgba(255,255,255,.15)'}}><div style={{width: `${(frame / durationInFrames) * 100}%`, height: '100%', background: PALETTE.accent, borderRadius: 3}} /></div>;
};
