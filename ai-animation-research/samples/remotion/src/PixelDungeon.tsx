import React, {useEffect, useRef} from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig, Easing} from 'remotion';
import {Caption, Flash, Finish, PALETTE, Progress, TitleCard} from './ui';

// "2D graphics in code": every frame is drawn procedurally into a tiny canvas (192x342 = 1080x1920 / 5.625)
// then scaled up with image smoothing OFF, so the pixel grid stays crisp. No image assets anywhere.
const W = 192, H = 342, TILE = 16;

// hue-shifted ramps (shadow -> highlight)
const STONE = ['#2b3350', '#3f4b6e', '#5a6b8c', '#7f90b0', '#aab8d2'];
const MOSS = ['#2d5a2b', '#3d7238', '#4f8a4a', '#6fae62', '#9fd48c'];
const WOOD = ['#4a2e1c', '#6b4229', '#8a5a3a', '#b07a52', '#d6a070'];
const FIRE = ['#8a2a16', '#d2541f', '#ffb13d', '#ffd877', '#fff3c4'];
const ARMOR = ['#2c4b7a', '#4a7fc0', '#7fb7ff', '#b4d5ff', '#e6f2ff'];
const SKIN = ['#a8785a', '#d3a37d', '#f2c9a0', '#f8dcbd', '#fff0de'];
const CLOTH = ['#6b1f2c', '#9f2e41', '#d6465a', '#ee7a88', '#ffb3bb'];
const SLIME = ['#3d6e1c', '#5fa52d', '#8be04a', '#b6f07e', '#e4ffc2'];
const INK = '#121420';

type Ctx = CanvasRenderingContext2D;
const px = (c: Ctx, x: number, y: number, col: string) => { c.fillStyle = col; c.fillRect(Math.round(x), Math.round(y), 1, 1); };
const rect = (c: Ctx, x: number, y: number, w: number, h: number, col: string) => { c.fillStyle = col; c.fillRect(Math.round(x), Math.round(y), w, h); };
const dither = (c: Ctx, x: number, y: number, w: number, h: number, a: string, b: string) => { for (let yy = 0; yy < h; yy++) for (let xx = 0; xx < w; xx++) px(c, x + xx, y + yy, (xx + yy) % 2 ? b : a); };
// deterministic hash noise (no Math.random: renders must be reproducible)
const hash = (x: number, y: number, s = 0) => { let h = (x * 374761393 + y * 668265263 + s * 2246822519) | 0; h = Math.imul(h ^ (h >>> 13), 1274126177); return ((h ^ (h >>> 16)) >>> 0) / 4294967295; };

const floorTile = (c: Ctx, x: number, y: number, seed: number) => {
  rect(c, x, y, TILE, TILE, STONE[2]);
  for (let i = 0; i < 14; i++) px(c, x + Math.floor(hash(i, seed) * 16), y + Math.floor(hash(seed, i) * 16), STONE[1]);
  for (let i = 0; i < 6; i++) px(c, x + Math.floor(hash(i + 40, seed) * 16), y + Math.floor(hash(seed, i + 40) * 16), STONE[3]);
  rect(c, x, y + 15, TILE, 1, STONE[0]); rect(c, x + 15, y, 1, TILE, STONE[0]);
  if (seed % 3 === 0) { rect(c, x + 3, y + 9, 4, 2, MOSS[2]); px(c, x + 7, y + 10, MOSS[3]); }
};
const wallTile = (c: Ctx, x: number, y: number) => {
  rect(c, x, y, TILE, TILE, STONE[1]);
  for (let row = 0; row < 4; row++) { const off = row % 2 ? 4 : 0; for (let bx = -1; bx < 3; bx++) { const xx = x + bx * 8 + off; c.save(); c.beginPath(); c.rect(x, y, TILE, TILE); c.clip(); rect(c, xx, y + row * 4, 7, 3, STONE[2]); rect(c, xx, y + row * 4, 7, 1, STONE[3]); c.restore(); } }
  rect(c, x, y, TILE, 1, STONE[3]);
};
const torch = (c: Ctx, x: number, y: number, f: number) => {
  rect(c, x + 7, y + 8, 2, 7, WOOD[2]); px(c, x + 7, y + 8, WOOD[3]);
  const flame = f % 2 ? [[7, 6], [8, 6], [8, 5], [7, 5], [8, 4], [7, 3]] : [[7, 6], [8, 6], [7, 5], [8, 5], [7, 4]];
  flame.forEach(([fx, fy], i) => px(c, x + fx, y + fy, i < 2 ? FIRE[4] : FIRE[3]));
  px(c, x + (f % 2 ? 7 : 8), y + 7, FIRE[2]);
};
// original hero 16x24; motion is parametric (bob, leg phase, sword swing), not hand-copied frames
const hero = (c: Ctx, x: number, y: number, f: number) => {
  const bob = f % 2, ph = f % 4;
  const [la, lb] = ph === 0 || ph === 2 ? [0, 0] : ph === 1 ? [-1, 1] : [1, -1];
  rect(c, x + 5 + la, y + 17 + bob, 3, 6 - bob, CLOTH[1]); rect(c, x + 9 + lb, y + 17 + bob, 3, 6 - bob, CLOTH[0]);
  rect(c, x + 5 + la, y + 22, 3, 2, INK); rect(c, x + 9 + lb, y + 22, 3, 2, INK);
  rect(c, x + 4, y + 10 + bob, 8, 8, ARMOR[2]); rect(c, x + 4, y + 10 + bob, 8, 2, ARMOR[3]); rect(c, x + 10, y + 12 + bob, 2, 5, ARMOR[1]);
  dither(c, x + 5, y + 14 + bob, 3, 3, ARMOR[2], ARMOR[1]);
  rect(c, x + 5, y + 3 + bob, 6, 7, SKIN[2]); rect(c, x + 5, y + 3 + bob, 6, 3, ARMOR[3]); rect(c, x + 4, y + 5 + bob, 8, 1, ARMOR[2]);
  px(c, x + 7, y + 7 + bob, INK); px(c, x + 9, y + 7 + bob, INK);
  px(c, x + 12, y + 4 + bob, CLOTH[3]); px(c, x + 12, y + 3 + bob, CLOTH[3]); px(c, x + 13, y + 2 + bob, CLOTH[2]);
  const sw = ph - 1;
  rect(c, x + 11, y + 12 + bob + sw, 2, 3, SKIN[1]);
  for (let i = 0; i < 6; i++) px(c, x + 13 + Math.floor(i / 3), y + 9 + bob + sw + i, i ? STONE[4] : FIRE[4]);
  // 1px selective outline (left/bottom) for readability against the floor
  rect(c, x + 3, y + 10 + bob, 1, 8, INK); rect(c, x + 4, y + 2 + bob, 8, 1, INK);
};
const slime = (c: Ctx, x: number, y: number, f: number) => {
  const sq = f % 2, w = 12 + 2 * sq, h = 9 - sq, y0 = y + 16 - h;
  for (let yy = 0; yy < h; yy++) { const t = (yy - h) / h; const r = yy < h - 1 ? Math.floor((w / 2) * Math.sqrt(Math.max(0, 1 - t * t))) : w / 2; rect(c, x + 8 - r, y0 + yy, 2 * r, 1, SLIME[2]); }
  rect(c, x + 8 - w / 2 + 2, y0 + 1, 3, 2, SLIME[4]);
  dither(c, x + 8 - w / 2 + 1, y + 13, w - 2, 2, SLIME[1], SLIME[0]);
  px(c, x + 6, y0 + 3, INK); px(c, x + 10, y0 + 3, INK);
};

// ---- the scene, as a pure function of the frame
const drawScene = (c: Ctx, frame: number) => {
  const t = frame / 30;
  const scroll = interpolate(frame, [60, 540], [0, 160], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  c.imageSmoothingEnabled = false;
  // sky / far parallax: dark gradient bands + distant towers
  rect(c, 0, 0, W, H, '#0b0f1a');
  for (let y = 0; y < 120; y++) rect(c, 0, y, W, 1, y < 40 ? '#10162a' : y < 80 ? '#141c36' : '#182240');
  for (let i = 0; i < 9; i++) { const tx = ((i * 37 - scroll * 0.2) % (W + 40) + W + 40) % (W + 40) - 20; const th = 30 + Math.floor(hash(i, 7) * 40); rect(c, tx, 120 - th, 12 + Math.floor(hash(i, 9) * 10), th, '#1c2748'); if (frame % 60 < 50) px(c, tx + 4, 120 - th + 6, FIRE[3]); }
  // mid parallax: wall band
  for (let i = -1; i <= W / TILE + 1; i++) { const wx = i * TILE - ((scroll * 0.5) % TILE); for (let r = 0; r < 4; r++) wallTile(c, wx, 120 + r * TILE); }
  // torches on the wall
  for (let i = 0; i < 6; i++) { const tx = ((i * 64 - scroll * 0.5) % (W + 64) + W + 64) % (W + 64) - 32; torch(c, tx, 150, Math.floor(frame / 4) + i); const glow = 0.12 + 0.05 * Math.sin(t * 9 + i); c.fillStyle = `rgba(255,177,61,${glow.toFixed(3)})`; c.fillRect(tx - 6, 148, 28, 20); }
  // floor
  for (let r = 0; r < 10; r++) for (let i = -1; i <= W / TILE + 1; i++) { const fx = i * TILE - (scroll % TILE); floorTile(c, fx, 184 + r * TILE, (i + Math.floor(scroll / TILE)) * 31 + r * 7); }
  // slimes bouncing along the floor
  for (let i = 0; i < 3; i++) { const sx = ((i * 70 + 40 - scroll) % (W + 40) + W + 40) % (W + 40) - 20; const hop = Math.abs(Math.sin(t * 4 + i)) * 6; slime(c, sx, 232 - hop, Math.floor(frame / 6) + i); }
  // hero walking in place (world scrolls)
  const walking = frame >= 60 && frame <= 540;
  hero(c, 88, 212, walking ? Math.floor(frame / 5) : 0);
  // hero light pool
  c.fillStyle = 'rgba(255,220,150,0.08)'; c.fillRect(70, 200, 52, 48);
  // HUD: hearts + coin counter drawn in pixels
  for (let i = 0; i < 3; i++) { const hx = 6 + i * 10, hy = 8; const full = i < (frame < 420 ? 3 : 2); const col = full ? CLOTH[2] : STONE[1]; rect(c, hx + 1, hy, 2, 1, col); rect(c, hx + 4, hy, 2, 1, col); rect(c, hx, hy + 1, 7, 2, col); rect(c, hx + 1, hy + 3, 5, 1, col); rect(c, hx + 2, hy + 4, 3, 1, col); px(c, hx + 3, hy + 5, col); }
  const coins = Math.floor(interpolate(frame, [60, 540], [0, 42], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));
  rect(c, W - 30, 7, 5, 5, FIRE[3]); px(c, W - 29, 8, FIRE[4]);
  const digits = String(coins).padStart(2, '0');
  // tiny 3x5 pixel font for digits
  const FONT: Record<string, string[]> = {'0': ['111','101','101','101','111'], '1': ['010','110','010','010','111'], '2': ['111','001','111','100','111'], '3': ['111','001','111','001','111'], '4': ['101','101','111','001','001'], '5': ['111','100','111','001','111'], '6': ['111','100','111','101','111'], '7': ['111','001','010','010','010'], '8': ['111','101','111','101','111'], '9': ['111','101','111','001','111']};
  [...digits].forEach((d, di) => FONT[d].forEach((row, ry) => [...row].forEach((bit, rx) => { if (bit === '1') px(c, W - 22 + di * 4 + rx, 7 + ry, STONE[4]); })));
  // scanlines for the CRT feel
  for (let y = 0; y < H; y += 2) { c.fillStyle = 'rgba(0,0,0,0.18)'; c.fillRect(0, y, W, 1); }
};

const PixelCanvas: React.FC = () => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const cv = ref.current; if (!cv) return;
    const c = cv.getContext('2d')!; drawScene(c, frame);
  }, [frame]);
  return <canvas ref={ref} width={W} height={H} style={{width, height, imageRendering: 'pixelated'}} />;
};

export const PixelDungeon: React.FC = () => (
  <AbsoluteFill style={{backgroundColor: PALETTE.bg}}>
    <PixelCanvas />
    <TitleCard text="This whole game|is drawn by code." start={0} end={60} sub="no sprites, no PNGs, no AI images" />
    <Flash at={60} />
    <Caption words="Every tile is a function. Every pixel is a decision." start={64} end={190} highlight={['function', 'decision']} y={1560} size={58} />
    <Caption words="Colours come from hue-shifted ramps, not one flat colour." start={196} end={330} highlight={['hue-shifted', 'ramps']} y={1560} size={58} />
    <Caption words="Motion is parameters: bob, leg phase, squash. Not copied frames." start={336} end={470} highlight={['parameters', 'squash']} y={1560} size={58} />
    <Caption words="Render tiny. Scale up with smoothing OFF." start={476} end={560} highlight={['OFF']} y={1560} size={58} />
    <Flash at={565} color={PALETTE.accent} />
    <TitleCard text="192 × 342 px|→ 1080 × 1920." start={565} end={660} sub="that's the pixel-art trick" />
    <Finish />
    <Progress />
  </AbsoluteFill>
);
