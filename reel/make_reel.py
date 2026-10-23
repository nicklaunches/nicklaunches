#!/usr/bin/env python3
"""Procedural pixel-art explainer reel: the honeybee waggle dance.

Renders 1080x1920 @ 60 fps (drawn at 270x480 and upscaled with nearest
neighbour for a crisp pixel look), ~56 s, with an original chiptune track.

Usage:
  python3 make_reel.py render OUT.mp4            # full render
  python3 make_reel.py frames OUTDIR t1 t2 ...   # dump PNGs at given seconds
"""
import math, os, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw

W, H = 270, 480          # native pixel canvas
SCALE = 4                # -> 1080 x 1920
FPS = 60
DURATION = 56.0
BPM = 120.0
BAR = 240.0 / BPM        # 2.0 s per bar = one dance circuit
SR = 48000

rng = np.random.default_rng(7)
random.seed(7)

# --------------------------------------------------------------------------
# 5x7 pixel font
# --------------------------------------------------------------------------
FONT_SRC = {
'A': ".###. #...# #...# ##### #...# #...# #...#",
'B': "####. #...# #...# ####. #...# #...# ####.",
'C': ".###. #...# #.... #.... #.... #...# .###.",
'D': "####. #...# #...# #...# #...# #...# ####.",
'E': "##### #.... #.... ####. #.... #.... #####",
'F': "##### #.... #.... ####. #.... #.... #....",
'G': ".###. #...# #.... #.### #...# #...# .####",
'H': "#...# #...# #...# ##### #...# #...# #...#",
'I': "##### ..#.. ..#.. ..#.. ..#.. ..#.. #####",
'J': "..### ...#. ...#. ...#. ...#. #..#. .##..",
'K': "#...# #..#. #.#.. ##... #.#.. #..#. #...#",
'L': "#.... #.... #.... #.... #.... #.... #####",
'M': "#...# ##.## #.#.# #.#.# #...# #...# #...#",
'N': "#...# ##..# #.#.# #..## #...# #...# #...#",
'O': ".###. #...# #...# #...# #...# #...# .###.",
'P': "####. #...# #...# ####. #.... #.... #....",
'Q': ".###. #...# #...# #...# #.#.# #..#. .##.#",
'R': "####. #...# #...# ####. #.#.. #..#. #...#",
'S': ".#### #.... #.... .###. ....# ....# ####.",
'T': "##### ..#.. ..#.. ..#.. ..#.. ..#.. ..#..",
'U': "#...# #...# #...# #...# #...# #...# .###.",
'V': "#...# #...# #...# #...# #...# .#.#. ..#..",
'W': "#...# #...# #...# #.#.# #.#.# ##.## #...#",
'X': "#...# #...# .#.#. ..#.. .#.#. #...# #...#",
'Y': "#...# #...# .#.#. ..#.. ..#.. ..#.. ..#..",
'Z': "##### ....# ...#. ..#.. .#... #.... #####",
'0': ".###. #...# #..## #.#.# ##..# #...# .###.",
'1': "..#.. .##.. ..#.. ..#.. ..#.. ..#.. .###.",
'2': ".###. #...# ....# ...#. ..#.. .#... #####",
'3': "##### ...#. ..#.. ...#. ....# #...# .###.",
'4': "...#. ..##. .#.#. #..#. ##### ...#. ...#.",
'5': "##### #.... ####. ....# ....# #...# .###.",
'6': "..##. .#... #.... ####. #...# #...# .###.",
'7': "##### ....# ...#. ..#.. .#... .#... .#...",
'8': ".###. #...# #...# .###. #...# #...# .###.",
'9': ".###. #...# #...# .#### ....# ...#. .##..",
'?': ".###. #...# ....# ...#. ..#.. ..... ..#..",
',': "..... ..... ..... ..... ..##. ..##. .#...",
'.': "..... ..... ..... ..... ..... ..##. ..##.",
"'": "..#.. ..#.. .#... ..... ..... ..... .....",
'@': ".###. #...# #.### #.#.# #.### #.... .###.",
':': "..... ..##. ..##. ..... ..##. ..##. .....",
'-': "..... ..... ..... ##### ..... ..... .....",
'!': "..#.. ..#.. ..#.. ..#.. ..#.. ..... ..#..",
'/': "....# ....# ...#. ..#.. .#... #.... #....",
' ': "..... ..... ..... ..... ..... ..... .....",
}
FONT = {k: np.array([[c == '#' for c in row] for row in v.split()], dtype=bool)
        for k, v in FONT_SRC.items()}

def text_bitmap(text):
    """Boolean HxW bitmap of a single line of text at 1px per font pixel."""
    cols = []
    for ch in text.upper():
        g = FONT.get(ch, FONT['?'])
        cols.append(g)
        cols.append(np.zeros((7, 1), dtype=bool))
    bm = np.concatenate(cols[:-1], axis=1) if cols else np.zeros((7, 0), bool)
    return bm

def upscale_bool(bm, s):
    return np.kron(bm, np.ones((s, s), dtype=bool))

_caption_cache = {}
def caption_layer(lines, color=(255, 255, 255), big=None, box=True, pad=4):
    """Pre-render a caption as an RGBA uint8 layer.
    lines: list of (text, scale). big is unused (kept for clarity)."""
    key = (tuple(lines), color, box, pad)
    if key in _caption_cache:
        return _caption_cache[key]
    bitmaps = [upscale_bool(text_bitmap(t), s) for t, s in lines]
    gap = 3
    tw = max(b.shape[1] for b in bitmaps)
    th = sum(b.shape[0] for b in bitmaps) + gap * (len(bitmaps) - 1)
    lw, lh = tw + 2 * pad + 2, th + 2 * pad + 2
    layer = np.zeros((lh, lw, 4), dtype=np.float32)
    if box:
        layer[..., :3] = 8.0
        layer[..., 3] = 180.0
    y = pad + 1
    for b in bitmaps:
        x = pad + 1 + (tw - b.shape[1]) // 2
        # shadow
        sh = np.zeros((lh, lw), bool)
        sh[y + 1:y + 1 + b.shape[0], x + 1:x + 1 + b.shape[1]] = b
        layer[sh, :3] = 0.0
        layer[sh, 3] = 255.0
        fg = np.zeros((lh, lw), bool)
        fg[y:y + b.shape[0], x:x + b.shape[1]] = b
        layer[fg, :3] = np.array(color, np.float32)
        layer[fg, 3] = 255.0
        y += b.shape[0] + gap
    _caption_cache[key] = layer
    return layer

# --------------------------------------------------------------------------
# blitting helpers (float32 frame, HxWx3)
# --------------------------------------------------------------------------
def blit_rgba(frame, layer, x, y, alpha=1.0):
    """Alpha-composite an RGBA float layer at integer (x, y) top-left."""
    lh, lw = layer.shape[:2]
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + lw, W), min(y + lh, H)
    if x1 <= x0 or y1 <= y0:
        return
    sub = layer[y0 - y:y1 - y, x0 - x:x1 - x]
    a = (sub[..., 3:4] / 255.0) * alpha
    dst = frame[y0:y1, x0:x1]
    dst[...] = dst * (1 - a) + sub[..., :3] * a

def add_rgb(frame, layer, x, y, gain=1.0):
    """Additive blend of an HxWx3 float layer."""
    lh, lw = layer.shape[:2]
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + lw, W), min(y + lh, H)
    if x1 <= x0 or y1 <= y0:
        return
    frame[y0:y1, x0:x1] += layer[y0 - y:y1 - y, x0 - x:x1 - x] * gain

def put_px(frame, x, y, color, size=1):
    x, y = int(round(x)), int(round(y))
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + size, W), min(y + size, H)
    if x1 > x0 and y1 > y0:
        frame[y0:y1, x0:x1] = color

def dotted_line(frame, p0, p1, color, step=4, size=1, phase=0.0):
    (x0, y0), (x1, y1) = p0, p1
    L = math.hypot(x1 - x0, y1 - y0)
    if L < 1:
        return
    n = int(L / step)
    for i in range(n + 1):
        u = (i * step + phase) / L
        if u > 1:
            break
        put_px(frame, x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, color, size)

def radial_kernel(r, power=2.0):
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    d = np.sqrt(xx ** 2 + yy ** 2) / r
    k = np.clip(1 - d, 0, 1) ** power
    return k.astype(np.float32)

GLOW_BIG = radial_kernel(44, 2.2)
GLOW_SMALL = radial_kernel(14, 1.8)
STAMP = radial_kernel(3, 1.2)

def stamp(buf, x, y, k, gain):
    r = k.shape[0] // 2
    xi, yi = int(round(x)), int(round(y))
    x0, y0 = max(xi - r, 0), max(yi - r, 0)
    x1, y1 = min(xi + r + 1, W), min(yi + r + 1, H)
    if x1 <= x0 or y1 <= y0:
        return
    buf[y0:y1, x0:x1] += k[y0 - (yi - r):y1 - (yi - r), x0 - (xi - r):x1 - (xi - r)] * gain

# --------------------------------------------------------------------------
# honeycomb background
# --------------------------------------------------------------------------
def build_honeycomb(seed=3, size=10.0):
    r = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    q = (math.sqrt(3) / 3 * xx - 1.0 / 3 * yy) / size
    rr = (2.0 / 3 * yy) / size
    # cube rounding
    x, z = q, rr
    y = -x - z
    rx, ry, rz = np.round(x), np.round(y), np.round(z)
    dx, dy, dz = np.abs(rx - x), np.abs(ry - y), np.abs(rz - z)
    m1 = (dx > dy) & (dx > dz)
    m2 = (~m1) & (dy > dz)
    rx = np.where(m1, -ry - rz, rx)
    rz = np.where(~m1 & ~m2, -rx - ry, rz)
    qi, ri = rx.astype(int), rz.astype(int)
    # centre of each hex in pixels
    cx = size * (math.sqrt(3) * qi + math.sqrt(3) / 2 * ri)
    cy = size * (1.5 * ri)
    # distance to centre normalised by inradius
    dxp, dyp = xx - cx, yy - cy
    # hex "radius" function (distance to edge in pointy-top hex)
    ang = np.arctan2(dyp, dxp)
    a = (ang + math.pi / 2) % (math.pi / 3) - math.pi / 6
    inr = size * math.sqrt(3) / 2
    d = np.sqrt(dxp ** 2 + dyp ** 2) * np.cos(a) / inr    # 0 centre, 1 edge
    key = (qi * 73856093) ^ (ri * 19349663)
    h = (np.abs(key) % 1000) / 1000.0
    # cell type
    base = np.zeros((H, W, 3), np.float32)
    dark = np.array([34, 18, 6], np.float32)
    amber = np.array([128, 70, 18], np.float32)
    honey = np.array([214, 138, 34], np.float32)
    mix = np.clip((h - 0.45) / 0.55, 0, 1)[..., None] ** 1.6
    col = dark * (1 - mix) + amber * mix
    bright = (h > 0.935)
    col = np.where(bright[..., None], honey * (0.75 + 0.25 * (h[..., None] - 0.9) / 0.1), col)
    # inner shading: lighter centre, dark rim
    shade = (1.15 - 0.45 * d ** 2)[..., None]
    col = col * shade
    rim = (d > 0.86)
    col[rim] = np.array([18, 9, 3], np.float32) + col[rim] * 0.25
    base = np.clip(col, 0, 255)
    # vignette
    vy, vx = np.mgrid[0:H, 0:W]
    v = 1 - 0.55 * (((vx - W / 2) / (W / 2)) ** 2 * 0.6 + ((vy - H / 2) / (H / 2)) ** 2) ** 1.2
    base *= np.clip(v, 0.25, 1)[..., None]
    shimmer = bright.astype(np.float32) * (0.5 + 0.5 * np.cos(h * 40.0))
    phase = h * 6.283
    return base.astype(np.float32), shimmer.astype(np.float32), phase.astype(np.float32)

HONEY_BASE, HONEY_SHIMMER, HONEY_PHASE = build_honeycomb()

def honeycomb(t):
    f = HONEY_BASE.copy()
    s = HONEY_SHIMMER * (0.5 + 0.5 * np.sin(HONEY_PHASE + t * 1.7))
    f += s[..., None] * np.array([40, 26, 6], np.float32)
    return f

# --------------------------------------------------------------------------
# bee sprites
# --------------------------------------------------------------------------
def make_bee_image(size=1.0, wing=0, blue=False):
    im = Image.new("RGBA", (16, 12), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    wing_col = (150, 190, 255, 190) if blue else (235, 240, 255, 150)
    if wing == 0:
        d.ellipse((4, 0, 9, 3), fill=wing_col)
        d.ellipse((4, 8, 9, 11), fill=wing_col)
    else:
        d.ellipse((5, 1, 8, 3), fill=wing_col)
        d.ellipse((5, 8, 8, 10), fill=wing_col)
    d.ellipse((1, 3, 11, 8), fill=(242, 182, 44, 255))
    px = im.load()
    for x in (3, 4, 7, 8):
        for y in range(3, 9):
            if px[x, y][3]:
                px[x, y] = (38, 26, 14, 255)
    d.ellipse((10, 3, 15, 8), fill=(50, 34, 18, 255))
    px[14, 4] = (240, 240, 240, 255)
    px[14, 7] = (240, 240, 240, 255)
    px[0, 5] = (38, 26, 14, 255)
    if size != 1.0:
        im = im.resize((max(1, int(16 * size)), max(1, int(12 * size))), Image.NEAREST)
    return im

ROT_STEP = 10
_bee_cache = {}
def bee_sprite(angle_deg, size=1.0, wing=0, blue=False):
    """RGBA float array for a bee facing screen angle `angle_deg` (clockwise from +x)."""
    a = int(round(angle_deg / ROT_STEP)) * ROT_STEP % 360
    key = (a, size, wing, blue)
    if key not in _bee_cache:
        im = make_bee_image(size, wing, blue).rotate(-a, resample=Image.NEAREST, expand=True)
        _bee_cache[key] = np.asarray(im).astype(np.float32)
    return _bee_cache[key]

def draw_bee(frame, x, y, heading_deg, t, size=1.0, blue=False, flap=True):
    wing = int(t * 30) % 2 if flap else 0
    spr = bee_sprite(heading_deg, size, wing, blue)
    blit_rgba(frame, spr, int(round(x - spr.shape[1] / 2)), int(round(y - spr.shape[0] / 2)))

def sun_icon(frame, x, y, r=4, t=0.0):
    stamp_layer = GLOW_SMALL
    add_rgb3(frame, stamp_layer, x, y, np.array([120, 90, 30], np.float32))
    for a in range(0, 360, 45):
        rr = r + 3 + (1 if int(t * 4 + a / 45) % 2 == 0 else 0)
        put_px(frame, x + rr * math.cos(math.radians(a)), y + rr * math.sin(math.radians(a)), (255, 225, 120))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    m = (xx ** 2 + yy ** 2) <= r * r
    x0, y0 = int(x) - r, int(y) - r
    sub = frame[y0:y0 + 2 * r + 1, x0:x0 + 2 * r + 1]
    if sub.shape[:2] == m.shape:
        sub[m] = np.array([255, 240, 160], np.float32)

def add_rgb3(frame, kernel, x, y, color):
    r = kernel.shape[0] // 2
    xi, yi = int(round(x)), int(round(y))
    x0, y0 = max(xi - r, 0), max(yi - r, 0)
    x1, y1 = min(xi + r + 1, W), min(yi + r + 1, H)
    if x1 <= x0 or y1 <= y0:
        return
    k = kernel[y0 - (yi - r):y1 - (yi - r), x0 - (xi - r):x1 - (xi - r)]
    frame[y0:y1, x0:x1] += k[..., None] * color

def flower_icon(frame, x, y):
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)):
        put_px(frame, x + dx * 2, y + dy * 2, (170, 90, 230), 2)
    put_px(frame, x, y, (255, 220, 80), 2)
    put_px(frame, x + 1, y + 4, (80, 170, 60), 1)
    put_px(frame, x + 1, y + 5, (80, 170, 60), 1)

# --------------------------------------------------------------------------
# dance kinematics
# --------------------------------------------------------------------------
def dance_state(t, centre, theta_deg, phase=0.0, waggle_frac_fn=None, L_fn=None, side0=1):
    """Return (x, y, heading_deg, in_waggle, u) for a figure-eight waggle dance.
    One circuit per BAR. theta is the waggle direction clockwise from straight up."""
    tt = t + phase * BAR
    k = int(tt // BAR)
    u = (tt - k * BAR) / BAR
    wf = waggle_frac_fn(k) if waggle_frac_fn else 0.5
    L = L_fn(k) if L_fn else 40.0
    th = math.radians(theta_deg)
    dx, dy = math.sin(th), -math.cos(th)
    cx, cy = centre
    p0 = (cx - dx * L / 2, cy - dy * L / 2)
    p1 = (cx + dx * L / 2, cy + dy * L / 2)
    side = side0 if k % 2 == 0 else -side0
    if u < wf:
        v = u / wf
        wig = math.sin(tt * 2 * math.pi * 14.0) * 2.4
        x = p0[0] + dx * L * v - dy * wig
        y = p0[1] + dy * L * v + dx * wig
        head = math.degrees(math.atan2(dy, dx)) + math.cos(tt * 2 * math.pi * 14.0) * 25
        return x, y, head, True, u, p0, p1
    v = (u - wf) / (1 - wf)
    v = v * v * (3 - 2 * v)  # ease
    phi0 = math.atan2(p1[1] - cy, p1[0] - cx)
    phi = phi0 + side * math.pi * v
    x = cx + (L / 2) * math.cos(phi)
    y = cy + (L / 2) * math.sin(phi)
    # tangent
    tx, ty = -math.sin(phi) * side, math.cos(phi) * side
    head = math.degrees(math.atan2(ty, tx))
    return x, y, head, False, u, p0, p1

# --------------------------------------------------------------------------
# ambient bees
# --------------------------------------------------------------------------
class Wanderer:
    def __init__(self, r, box=(0, 0, W, H), size=None):
        self.x = r.uniform(box[0], box[2]); self.y = r.uniform(box[1], box[3])
        self.h = r.uniform(0, 360); self.speed = r.uniform(4, 10)
        self.turn = r.uniform(-30, 30); self.size = size or r.uniform(1.2, 1.6)
        self.seed = r.uniform(0, 100); self.box = box
    def step(self, dt, t):
        self.h += self.turn * dt + 40 * math.sin(t * 0.7 + self.seed) * dt
        self.x += math.cos(math.radians(self.h)) * self.speed * dt
        self.y += math.sin(math.radians(self.h)) * self.speed * dt
        x0, y0, x1, y1 = self.box
        if self.x < x0: self.x = x1
        if self.x > x1: self.x = x0
        if self.y < y0: self.y = y1
        if self.y > y1: self.y = y0

AMBIENT = [Wanderer(random.Random(i)) for i in range(26)]

# --------------------------------------------------------------------------
# meadow background
# --------------------------------------------------------------------------
HORIZON = 192
SUN_M = (135, 186)
FLOWERS_M = (205, 204)
HIVE_M = (135, 436)

def build_meadow(seed=11):
    r = np.random.default_rng(seed)
    f = np.zeros((H, W, 3), np.float32)
    yy = np.arange(H, dtype=np.float32)
    # sky gradient
    top = np.array([118, 78, 168], np.float32)
    mid = np.array([238, 168, 150], np.float32)
    low = np.array([252, 224, 170], np.float32)
    for y in range(HORIZON):
        u = y / HORIZON
        c = top * (1 - u) + mid * u if u < 0.6 else mid * (1 - (u - 0.6) / 0.4) + low * ((u - 0.6) / 0.4)
        if u < 0.6:
            c = top * (1 - u / 0.6) + mid * (u / 0.6)
        f[y, :] = c
    # bands of cloud / dither in sky
    for y in range(0, HORIZON, 3):
        n = r.random(W) < 0.18
        f[y, n] += 14
    # ground
    far = np.array([168, 212, 96], np.float32)
    near = np.array([42, 112, 40], np.float32)
    for y in range(HORIZON, H):
        u = ((y - HORIZON) / (H - HORIZON)) ** 0.7
        f[y, :] = far * (1 - u) + near * u
    gy, gx = np.mgrid[HORIZON:H, 0:W]
    noise = r.random((H - HORIZON, W))
    dens = ((gy - HORIZON) / (H - HORIZON))
    dark = noise < (0.08 + 0.25 * dens)
    light = noise > (0.97 - 0.05 * dens)
    g = f[HORIZON:H]
    g[dark] *= 0.72
    g[light] = g[light] * 0.6 + np.array([190, 230, 120], np.float32) * 0.4
    # blades near bottom
    for _ in range(600):
        x = int(r.integers(0, W)); y = int(r.integers(HORIZON + 60, H))
        hgt = int(2 + (y - HORIZON) / 60)
        f[max(0, y - hgt):y, x] = f[max(0, y - hgt):y, x] * 0.5 + np.array([120, 190, 70], np.float32) * 0.5
    # scattered wildflowers
    for _ in range(260):
        x = int(r.integers(0, W)); y = int(r.integers(HORIZON + 8, H))
        c = [(250, 250, 230), (255, 230, 90), (200, 150, 250)][int(r.integers(0, 3))]
        sz = 1 if y < HORIZON + 120 else 2
        f[y:y + sz, x:x + sz] = c
    # sun glow
    add_rgb3(f, radial_kernel(70, 2.5), SUN_M[0], SUN_M[1], np.array([160, 110, 60], np.float32))
    add_rgb3(f, radial_kernel(26, 1.6), SUN_M[0], SUN_M[1], np.array([120, 110, 80], np.float32))
    # sun disc (half above horizon)
    yy2, xx2 = np.mgrid[0:H, 0:W]
    disc = ((xx2 - SUN_M[0]) ** 2 + (yy2 - SUN_M[1]) ** 2 <= 13 ** 2) & (yy2 < HORIZON)
    f[disc] = np.array([255, 246, 190], np.float32)
    # horizon haze line
    f[HORIZON - 1:HORIZON + 1] = f[HORIZON - 1:HORIZON + 1] * 0.5 + 110
    return np.clip(f, 0, 255)

MEADOW = build_meadow()

def meadow(t):
    f = MEADOW.copy()
    # rays from sun, slowly rotating
    for i in range(10):
        a = math.radians(-90 + (i - 4.5) * 9 + 2 * math.sin(t * 0.6 + i))
        for s in range(20, 140, 5):
            x = SUN_M[0] + math.cos(a) * s; y = SUN_M[1] + math.sin(a) * s
            if 0 <= y < HORIZON and 0 <= x < W:
                f[int(y), int(x)] += 22
    return f

def hive_box(frame, x, y, label=None):
    """Pixel hive box standing on the meadow, bottom-centre at (x, y)."""
    layer = Image.new("RGBA", (104, 56), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.polygon([(12, 16), (92, 16), (96, 54), (8, 54)], fill=(96, 60, 30, 255))
    d.rectangle((8, 16, 96, 18), fill=(60, 38, 18, 255))
    d.polygon([(2, 16), (102, 16), (90, 2), (14, 2)], fill=(124, 80, 40, 255))
    d.rectangle((9, 36, 95, 37), fill=(66, 42, 20, 255))
    d.rectangle((38, 48, 66, 51), fill=(20, 12, 6, 255))      # entrance
    d.rectangle((8, 54, 96, 55), fill=(40, 26, 12, 255))
    arr = np.asarray(layer).astype(np.float32)
    blit_rgba(frame, arr, int(x - 52), int(y - 56))
    if label:
        lay = caption_layer([(label, 1)], color=(236, 206, 140), box=False, pad=0)
        blit_rgba(frame, lay, int(x - lay.shape[1] / 2), int(y - 33))

# --------------------------------------------------------------------------
# scene timeline
# --------------------------------------------------------------------------
THETA0 = 35.0   # waggle direction, clockwise from "up" (sun)

CAPTIONS = [
    (0.0, 2.6,  [("BEE WAGGLE", 2), ("DANCE", 2)], (255, 255, 255)),
    (2.6, 6.2,  [("THIS BEE IS", 1), ("DRAWING A MAP", 1)], (255, 255, 255)),
    (6.2, 9.2,  [("CAN YOU", 2), ("READ IT?", 2)], (255, 226, 110)),
    (9.2, 12.6, [("STRAIGHT UP", 1), ("MEANS THE SUN", 1)], (255, 255, 255)),
    (12.6, 16.4,[("HER TILT POINTS", 1), ("TO THE FLOWERS", 1)], (255, 255, 255)),
    (16.4, 20.0,[("THE LONGER THE", 1), ("WAGGLE, THE FARTHER", 1)], (255, 255, 255)),
    (20.0, 23.6,[("ABOUT", 1), ("1 SECOND", 2), ("PER KILOMETRE", 1)], (255, 255, 255)),
    (23.6, 28.4,[("SISTERS FEEL IT", 1), ("IN THE DARK", 1)], (255, 255, 255)),
    (35.0, 39.0,[("1 KM, RIGHT", 2), ("OF THE SUN", 1)], (255, 255, 255)),
    (43.4, 47.2,[("THE SUN MOVES,", 1), ("THE DANCE TURNS", 1)], (255, 255, 255)),
    (47.2, 51.2,[("SHE TRACKS AN", 1), ("UNSEEN SUN", 2)], (255, 255, 255)),
    (51.6, 55.0,[("DECODED BY KARL VON FRISCH", 1), ("NOBEL PRIZE 1973", 1)], (255, 226, 110)),
]

def fade_in_out(t, t0, t1, f=0.25):
    if t < t0 or t > t1:
        return 0.0
    return min(1.0, (t - t0) / f, (t1 - t) / f)

def draw_captions(frame, t):
    for t0, t1, lines, color in CAPTIONS:
        a = fade_in_out(t, t0, t1)
        if a <= 0:
            continue
        lay = caption_layer(lines, color)
        y = 34 if t < 51.5 else 400
        blit_rgba(frame, lay, (W - lay.shape[1]) // 2, y, a)
    if 0.0 <= t < 2.6:
        # headphones glyph under the title
        a = fade_in_out(t, 0, 2.6)
        hp = np.array([[c == '#' for c in row] for row in
                       ".#####. #.....# #.....# ##...## ##...## ##...##".split()], bool)
        lay = np.zeros(hp.shape + (4,), np.float32)
        lay[hp, :3] = 230; lay[hp, 3] = 255
        blit_rgba(frame, lay, W // 2 - 3, 104, a)

# dance schedule per circuit index k (BAR = 2 s)
def waggle_frac(k):
    if k == 8: return 0.32
    if k == 9: return 0.72
    return 0.5

def waggle_len(k):
    if k == 8: return 24.0
    if k == 9: return 60.0
    return 40.0

DANCE_C = (135.0, 232.0)
TRAIL = np.zeros((H, W), np.float32)
TRAIL_DECAY = 0.9945
_last_pos = {}
AMBER = np.array([255, 185, 70], np.float32)

def stamp_trail(key, x, y, gain):
    lx, ly = _last_pos.get(key, (x, y))
    n = max(1, int(math.hypot(x - lx, y - ly) / 1.0))
    for i in range(1, n + 1):
        u = i / n
        stamp(TRAIL, lx + (x - lx) * u, ly + (y - ly) * u, STAMP, gain / n)
    _last_pos[key] = (x, y)

def theta_at(t):
    """Waggle direction over time: fixed, then turning as the sun moves (43-51 s)."""
    if t < 43.0:
        return THETA0
    u = min(1.0, max(0.0, (t - 43.4) / 7.6))
    u = u * u * (3 - 2 * u)
    return THETA0 - 70.0 * u

def render_hive(t, dt):
    global TRAIL
    f = honeycomb(t)
    TRAIL *= TRAIL_DECAY
    th = theta_at(t)
    second_act = t >= 43.0
    # ambient bees
    for b in AMBIENT:
        b.step(dt, t)
    # dancers
    dancers = [("main", DANCE_C, 0.0, 1)]
    if second_act:
        dancers += [("d2", (62.0, 130.0), 0.37, -1), ("d3", (212.0, 118.0), 0.71, 1),
                    ("d4", (70.0, 372.0), 0.12, -1), ("d5", (210.0, 352.0), 0.55, 1)]
    states = {}
    for key, c, ph, s0 in dancers:
        x, y, head, wag, u, p0, p1 = dance_state(t, c, th, ph, waggle_frac, waggle_len, s0)
        states[key] = (x, y, head, wag, u, p0, p1)
        if t > 2.4:
            stamp_trail(key, x, y, 1.5 if wag else 0.8)
    # trail composite
    tr = np.clip(TRAIL, 0, 1.1)
    f += tr[..., None] * AMBER
    # ambient bees (behind glow)
    for b in AMBIENT:
        if t >= 23.6 and t < 43.0 and b is AMBIENT[0]:
            pass
        draw_bee(f, b.x, b.y, b.h, t, b.size)
    # sister bees attending the dancer
    mx, my, mh, mwag, mu, p0, p1 = states["main"]
    n_sis = 3 if t < 23.6 else min(7, 3 + int((t - 23.6) * 2))
    for i in range(n_sis):
        a = t * 0.35 + i * (2 * math.pi / 7) + math.sin(t * 0.9 + i) * 0.3
        r = 34 + 4 * math.sin(t * 1.3 + i * 1.7)
        sx, sy = mx + r * math.cos(a), my + r * math.sin(a)
        hd = math.degrees(math.atan2(my - sy, mx - sx)) + 10 * math.sin(t * 6 + i)
        draw_bee(f, sx, sy, hd, t, 1.4)
    # glow and dancers
    for key, (x, y, head, wag, u, q0, q1) in states.items():
        add_rgb3(f, GLOW_BIG, x, y, np.array([110, 62, 10], np.float32) * (1.0 if wag else 0.6))
        draw_bee(f, x, y, head, t, 2.0)
    # explanatory overlays (first act)
    if 9.2 <= t < 16.6:
        a = fade_in_out(t, 9.2, 16.6)
        col = tuple(int(c * a) for c in (255, 235, 150))
        top = 92
        dotted_line(f, (p0[0], p0[1]), (p0[0], top + 10), col, step=4, size=1, phase=(t * 20) % 4)
        sun_icon(f, p0[0], top, r=4, t=t)
        if t >= 12.6:
            b = fade_in_out(t, 12.6, 16.6)
            thr = math.radians(THETA0)
            L = 118
            ex, ey = p0[0] + math.sin(thr) * L, p0[1] - math.cos(thr) * L
            colb = tuple(int(c * b) for c in (210, 170, 255))
            dotted_line(f, (p0[0], p0[1]), (ex, ey), colb, step=4, size=1, phase=(t * 20) % 4)
            flower_icon(f, ex, ey)
            # angle arc
            for ang in np.arange(0, THETA0, 6):
                ar = math.radians(ang)
                put_px(f, p0[0] + math.sin(ar) * 20, p0[1] - math.cos(ar) * 20, colb, 1)
    if 16.4 <= t < 20.0:
        # ruler under the waggle run
        a = fade_in_out(t, 16.4, 20.0)
        col = tuple(int(c * a) for c in (255, 235, 150))
        dotted_line(f, p0, p1, col, step=3, size=1)
        for q in (p0, p1):
            put_px(f, q[0] - 1, q[1] - 1, col, 3)
    if 20.0 <= t < 23.6:
        # one-second timer bar under the caption, fills during the waggle
        a = fade_in_out(t, 20.0, 23.6)
        bx, by, bw = 95, 118, 80
        f[by:by + 4, bx:bx + bw] = f[by:by + 4, bx:bx + bw] * (1 - 0.7 * a) + 10 * a
        wu = min(1.0, mu / 0.5) if mwag else 1.0
        fill = int(bw * wu)
        f[by + 1:by + 3, bx:bx + fill] = f[by + 1:by + 3, bx:bx + fill] * (1 - a) + np.array([255, 226, 110], np.float32) * a
    if second_act:
        # small entrance window at the bottom showing the moving sun
        wx, wy, ww, wh = 110, 448, 50, 12
        a = fade_in_out(t, 43.0, 51.6, 0.5)
        win = MEADOW[HORIZON - 70:HORIZON - 58, 110:160].copy() * 0.85
        win[9:12] = np.array([70, 120, 50], np.float32)
        sx = int(wx + 4 + (ww - 8) * min(1.0, max(0.0, (t - 43.4) / 7.6)))
        win[3:7, max(0, sx - wx - 2):sx - wx + 2] = np.array([255, 250, 200], np.float32)
        f[wy:wy + wh, wx:wx + ww] = f[wy:wy + wh, wx:wx + ww] * (1 - a) + win * a
        f[wy - 1, wx - 1:wx + ww + 1] *= (1 - 0.5 * a)
    return f

# meadow bee streams
class Flyer:
    def __init__(self, i):
        r = random.Random(100 + i)
        self.t0 = 29.2 + i * 0.09 + r.uniform(0, 0.15)
        self.dur = r.uniform(2.6, 3.4)
        self.side = r.uniform(-1, 1)
        self.jit = r.uniform(0, 10)
        self.ret = r.random() < 0.35
    def pos(self, t):
        u = (t - self.t0) / self.dur
        if u < 0 or u > 1.0:
            return None
        x0, y0 = HIVE_M[0] + self.side * 10, HIVE_M[1] - 20
        x1, y1 = FLOWERS_M
        uu = u ** 0.85
        x = x0 + (x1 - x0) * uu + self.side * 26 * math.sin(math.pi * uu)
        y = y0 + (y1 - y0) * uu + 6 * math.sin(uu * 6 + self.jit)
        s = 1.0 - 0.8 * uu
        return x, y, s

FLYERS = [Flyer(i) for i in range(48)]

def render_meadow(t, dt):
    f = meadow(t)
    # flowers appear
    fa = min(1.0, max(0.0, (t - 31.5) / 2.5))
    if fa > 0:
        r = np.random.default_rng(5)
        n = int(160 * fa)
        pts = r.normal(0, 1, (160, 2))
        for i in range(n):
            px_, py_ = FLOWERS_M[0] + pts[i, 0] * 15, FLOWERS_M[1] + pts[i, 1] * 3.5
            c = (175, 95, 235) if i % 3 else (215, 150, 255)
            put_px(f, px_, py_, c, 1)
        add_rgb3(f, radial_kernel(22, 1.5), FLOWERS_M[0], FLOWERS_M[1], np.array([90, 30, 120], np.float32) * fa)
    # bees flying out
    for fl in FLYERS:
        p = fl.pos(t)
        if p:
            x, y, s = p
            if s > 0.5:
                draw_bee(f, x, y, -60 + fl.side * 20, t, 0.7 * s / 1.0)
            else:
                put_px(f, x, y, (250, 200, 60), 2 if s > 0.3 else 1)
            # sparkle trail
            put_px(f, x - 2, y + 2, (255, 230, 150), 1)
    # diagram
    if 35.0 <= t < 43.4:
        a = fade_in_out(t, 35.0, 43.4, 0.4)
        col = tuple(int(c * a) for c in (255, 245, 200))
        colb = tuple(int(c * a) for c in (210, 170, 255))
        ph = (t * 16) % 4
        dotted_line(f, HIVE_M, (SUN_M[0], SUN_M[1] + 14), col, step=4, size=1, phase=ph)
        dotted_line(f, HIVE_M, FLOWERS_M, colb, step=4, size=1, phase=ph)
        ang = math.atan2(FLOWERS_M[0] - HIVE_M[0], HIVE_M[1] - FLOWERS_M[1])
        for q in np.arange(0, ang, 0.08):
            put_px(f, HIVE_M[0] + math.sin(q) * 28, HIVE_M[1] - math.cos(q) * 28, colb, 1)
        put_px(f, HIVE_M[0] - 1, HIVE_M[1] - 1, col, 3)
    if t >= 39.0:
        a = fade_in_out(t, 39.0, 43.4, 0.3)
        tmp = f.copy()
        hive_box(tmp, HIVE_M[0], HIVE_M[1] + 24, label="@NICKLAUNCHES")
        f = f * (1 - a) + tmp * a
    return f

# --------------------------------------------------------------------------
# frame assembly with transitions
# --------------------------------------------------------------------------
def render_frame(t, dt):
    if t < 29.0:
        f = render_hive(t, dt)
        if t >= 26.6:
            # pull back: hive view shrinks into a wooden frame; entrance light grows
            u = (t - 26.6) / 2.4
            u = u * u * (3 - 2 * u)
            s = 1.0 - 0.42 * u
            img = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8))
            nw, nh = int(W * s), int(H * s)
            small = np.asarray(img.resize((nw, nh), Image.NEAREST)).astype(np.float32)
            bg = np.zeros((H, W, 3), np.float32) + np.array([24, 14, 6], np.float32)
            ox, oy = (W - nw) // 2, int(10 * u)
            bg[oy:oy + nh, ox:ox + nw] = small
            # wooden frame
            bg[max(0, oy - 4):oy, :] = np.array([70, 44, 20], np.float32)
            bg[:, max(0, ox - 4):ox] = np.array([70, 44, 20], np.float32)
            bg[:, ox + nw:ox + nw + 4] = np.array([70, 44, 20], np.float32)
            bg[oy + nh:oy + nh + 4, :] = np.array([70, 44, 20], np.float32)
            # entrance slit of daylight at the bottom
            sw = int(30 + 110 * u); sh = int(4 + 40 * u)
            x0 = W // 2 - sw // 2; y0 = H - 10 - sh
            win = MEADOW[HORIZON - sh // 2:HORIZON - sh // 2 + sh, W // 2 - sw // 2:W // 2 - sw // 2 + sw]
            bg[y0:y0 + sh, x0:x0 + sw] = win
            f = bg
        return f
    if t < 43.4:
        f = render_meadow(t, dt)
        if t < 29.6:
            f = f * (0.3 + 0.7 * (t - 29.0) / 0.6) + 255 * max(0.0, 1 - (t - 29.0) / 0.25)
        if t >= 42.4:
            # dive into the hive entrance: zoom + darken
            u = (t - 42.4) / 1.0
            z = 1.0 + 2.2 * u
            img = Image.fromarray(np.clip(f, 0, 255).astype(np.uint8))
            cx, cy = HIVE_M[0], HIVE_M[1] + 20
            cw, ch = int(W / z), int(H / z)
            box = (int(cx - cw / 2), int(cy - ch / 2), int(cx - cw / 2) + cw, int(cy - ch / 2) + ch)
            box = (max(0, min(box[0], W - cw)), max(0, min(box[1], H - ch)))
            img = img.crop((box[0], box[1], box[0] + cw, box[1] + ch)).resize((W, H), Image.NEAREST)
            f = np.asarray(img).astype(np.float32) * (1 - u)
        return f
    f = render_hive(t, dt)
    if t < 44.0:
        f = f * ((t - 43.4) / 0.6)
    if t >= 54.6:
        f = f * max(0.0, 1 - (t - 54.6) / 1.2)
    return f

def frame_rgb(t, dt=1.0 / FPS):
    f = render_frame(t, dt)
    draw_captions(f, t)
    return np.clip(f, 0, 255).astype(np.uint8)

# --------------------------------------------------------------------------
# audio: original chiptune + bee buzz
# --------------------------------------------------------------------------
def note(n):  # midi -> Hz
    return 440.0 * 2 ** ((n - 69) / 12)

def env(n, a, d, s, r, total):
    e = np.ones(total, np.float32)
    a_, d_, r_ = int(a * SR), int(d * SR), int(r * SR)
    if a_ > 0: e[:a_] = np.linspace(0, 1, a_)
    if d_ > 0: e[a_:a_ + d_] = np.linspace(1, s, d_)
    e[a_ + d_:] = s
    if r_ > 0 and r_ < total: e[-r_:] *= np.linspace(1, 0, r_)
    return e

def pulse(freq, n, duty=0.25, vib=0.0):
    t = np.arange(n) / SR
    ph = (freq * t + vib * np.sin(2 * np.pi * 5.5 * t) / 100) % 1.0
    return np.where(ph < duty, 1.0, -1.0).astype(np.float32)

def tri(freq, n):
    t = np.arange(n) / SR
    return (2 * np.abs(2 * ((freq * t) % 1.0) - 1) - 1).astype(np.float32)

def soften(x, k=12):
    ker = np.hanning(k).astype(np.float32); ker /= ker.sum()
    return np.convolve(x, ker, mode="same")

def build_audio():
    total = int(DURATION * SR)
    mix = np.zeros(total, np.float32)
    r = np.random.default_rng(21)
    beat = 60.0 / BPM
    nbars = int(DURATION / BAR) + 1
    chords = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [48, 52, 55]), (55, [55, 59, 62])]  # Am F C G
    pent = [69, 72, 74, 76, 79, 81, 84]
    lead_patterns = [
        [0, 2, 4, 2, 5, 4, 2, 0], [4, 5, 6, 5, 4, 2, 4, 2],
        [0, 4, 2, 5, 4, 6, 5, 4], [6, 5, 4, 2, 4, 2, 0, 2]]
    def add(seg, start):
        s = int(start * SR); e = min(total, s + len(seg))
        if e > s: mix[s:e] += seg[:e - s]
    for bar in range(nbars):
        t0 = bar * BAR
        root, chord = chords[bar % 4]
        bright = 14 <= bar < 22          # meadow section
        quiet = bar >= 26
        # bass: root on each beat, octave bounce on the off-beats
        for b in range(4):
            for half in range(2):
                n = int(beat / 2 * SR)
                freq = note(root - 12 + (12 if half else 0) - (0 if bright else 0))
                seg = pulse(freq, n, 0.5) * env(n, 0.004, 0.08, 0.35, 0.03, n) * (0.16 if not quiet else 0.08)
                add(soften(seg, 24), t0 + b * beat + half * beat / 2)
        # lead arpeggio (8ths)
        if bar >= 2 and not quiet:
            pat = lead_patterns[(bar // 2) % 4]
            for i, p in enumerate(pat):
                n = int(beat / 2 * SR)
                m = pent[p] + (12 if bright and i % 2 == 0 else 0)
                seg = pulse(note(m), n, 0.25, vib=1.2) * env(n, 0.003, 0.12, 0.45, 0.05, n) * 0.11
                add(soften(seg, 10), t0 + i * beat / 2)
        # pad chords in the meadow and at the end
        if bright or bar >= 22:
            n = int(BAR * SR)
            seg = np.zeros(n, np.float32)
            for m in chord:
                seg += tri(note(m + 12), n) + tri(note(m + 12) * 1.004, n) * 0.6
            seg = seg * env(n, 0.3, 0.2, 0.8, 0.6, n) * (0.045 if not quiet else 0.03)
            add(soften(seg, 40), t0)
        # drums
        for b in range(4):
            tb = t0 + b * beat
            # kick
            n = int(0.22 * SR); tt = np.arange(n) / SR
            kick = np.sin(2 * np.pi * (150 * np.exp(-tt * 18) + 40) * tt) * np.exp(-tt * 16) * 0.42
            if b in (0, 2) or (b == 3 and bar % 2 == 1):
                add(kick.astype(np.float32), tb)
            # snare from bar 2
            if bar >= 2 and b in (1, 3):
                n = int(0.16 * SR); tt = np.arange(n) / SR
                sn = (r.normal(0, 1, n) * 0.5 + np.sin(2 * np.pi * 190 * tt) * 0.5) * np.exp(-tt * 26) * 0.26
                add(sn.astype(np.float32), tb)
            # hats on 8ths
            for half in range(2):
                n = int(0.05 * SR); tt = np.arange(n) / SR
                hat = r.normal(0, 1, n) * np.exp(-tt * (90 if half else 60)) * (0.07 if half else 0.1)
                add(hat.astype(np.float32), tb + half * beat / 2)
    # bee buzz during waggle runs in the hive sections
    for k in range(nbars):
        t0 = k * BAR
        if 29.0 <= t0 < 43.0:
            continue
        wf = waggle_frac(k)
        n = int(wf * BAR * SR); tt = np.arange(n) / SR
        f0 = 215 + 12 * np.sin(2 * np.pi * 0.9 * tt)
        saw = (2 * ((np.cumsum(f0) / SR) % 1.0) - 1)
        am = 0.6 + 0.4 * np.sin(2 * np.pi * 14 * tt)
        buzz = saw * am * env(n, 0.03, 0.05, 0.9, 0.08, n) * 0.11
        add(soften(buzz.astype(np.float32), 30), t0 + 0.0 if t0 >= 2.4 else t0)
    # meadow wind / sparkle: filtered noise swell
    n = int(14 * SR); tt = np.arange(n) / SR
    wind = soften(r.normal(0, 1, n).astype(np.float32), 400) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.25 * tt)) * 0.9
    add(wind * env(n, 1.5, 0, 1, 2.0, n), 29.0)
    # ending fade
    fade = np.ones(total, np.float32)
    fs = int(54.0 * SR); fade[fs:] = np.linspace(1, 0, total - fs)
    mix *= fade
    mix = np.tanh(mix * 1.6)
    mix *= 0.85 / max(1e-6, np.abs(mix).max())
    # gentle stereo: slight haas offset
    right = np.roll(mix, 180); right[:180] = 0
    st = np.stack([mix, right * 0.92 + mix * 0.08], axis=1)
    return (st * 32767).astype(np.int16)

def write_wav(path, data):
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(data.tobytes())

# --------------------------------------------------------------------------
def main():
    cmd = sys.argv[1]
    if cmd == "frames":
        outdir = sys.argv[2]; os.makedirs(outdir, exist_ok=True)
        times = [float(x) for x in sys.argv[3:]]
        # warm up the simulation up to each requested time so trails/bees look right
        t = 0.0; dt = 1.0 / 30
        for target in times:
            while t < target:
                frame_rgb(t, dt); t += dt
            img = Image.fromarray(frame_rgb(target, dt)).resize((W * SCALE, H * SCALE), Image.NEAREST)
            img.save(os.path.join(outdir, f"t{target:05.1f}.png"))
            print("wrote", target)
        return
    if cmd == "audio":
        write_wav(sys.argv[2], build_audio()); return
    out = sys.argv[2]
    wav = out + ".wav"
    write_wav(wav, build_audio())
    n = int(DURATION * FPS)
    ff = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
          "-vf", f"scale={W*SCALE}:{H*SCALE}:flags=neighbor",
          "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
          "-profile:v", "high", "-level", "4.2", "-movflags", "+faststart",
          "-c:a", "aac", "-b:a", "160k", "-shortest", out]
    p = subprocess.Popen(ff, stdin=subprocess.PIPE)
    dt = 1.0 / FPS
    for i in range(n):
        p.stdin.write(frame_rgb(i * dt, dt).tobytes())
        if i % 600 == 0:
            print(f"{i}/{n}", flush=True)
    p.stdin.close(); p.wait()
    os.remove(wav)
    print("done", out)

if __name__ == "__main__":
    main()
