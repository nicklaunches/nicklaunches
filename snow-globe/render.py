#!/usr/bin/env python3
"""
Snow Globe Village -- an original pixel-art animation with synthesized audio.

A tiny village inside a snow globe. The snow settles, the windows light up one
at a time (each one plays the next note of a lullaby), twelve glittering flakes
chime as they land, the clock tower lights last on a warm chord, and then a
curious cat nudges the glass.

Output: 1080x1920 (9:16), 60 fps, 40 s, H.264 + AAC.

Usage:
    python3 render.py snow_globe_village.mp4      # full render (~2-3 min)
    python3 render.py --preview 2,9,20,31,36,39   # dump stills at those seconds

Dependencies: numpy, Pillow, ffmpeg (with libx264 + aac).
Everything (art, melody, timing) is generated procedurally by this script.
"""
import math
import os
import random
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw

# ----------------------------------------------------------------------------
# Global constants
# ----------------------------------------------------------------------------
W, H = 180, 320            # internal pixel-art canvas
SCALE = 6                  # 180x320 -> 1080x1920
FPS = 60
DUR = 40.0
NF = int(DUR * FPS)
SR = 48000

# Globe ellipse (interior) and base
GCX, GCY, GRX, GRY = 90, 138, 76, 88
BASE_TOP = GCY + GRY - 10      # 216
BASE_BOT = BASE_TOP + 36       # 252
PIVOT = (GCX, BASE_BOT)

# Timeline (seconds)
T_TITLE = (0.6, 3.8)
WINDOW_TIMES = [6.0, 7.6, 9.2, 10.4, 12.4, 14.0, 15.6, 16.8, 18.8, 20.4, 22.0, 23.2]
MELODY = [67, 71, 74, 71, 69, 67, 64, 67, 69, 71, 74, 69]   # G4 B4 D5 B4 A4 G4 E4 G4 A4 B4 D5 A4
GLITTER_TIMES = [4.5, 6.8, 8.4, 11.2, 13.2, 15.0, 17.6, 19.6, 21.2, 24.4, 25.8, 27.4]
CHIME_HZ = [2349, 1976, 1568, 1760, 2637, 1976, 2349, 1568, 1760, 2637, 1976, 2349]
T_HANDLE = 28.0
T_CLOCK = 29.5
T_CAT = 32.5
T_EYES = 34.2
T_PAW = 35.0
T_HIT = 35.6
T_PAW_BACK = 37.0
T_BLINK = 38.6

rng = random.Random(7)

# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def lerp(a, b, t):
    return a + (b - a) * t


def lerpc(c0, c1, t):
    return tuple(int(round(lerp(c0[i], c1[i], t))) for i in range(3))


# ----------------------------------------------------------------------------
# Tiny pixel font (variable width, 5 rows)
# ----------------------------------------------------------------------------
FONT = {
    'A': [".X.", "X.X", "XXX", "X.X", "X.X"],
    'B': ["XX.", "X.X", "XX.", "X.X", "XX."],
    'C': [".XX", "X..", "X..", "X..", ".XX"],
    'E': ["XXX", "X..", "XX.", "X..", "XXX"],
    'G': [".XX", "X..", "X.X", "X.X", ".XX"],
    'H': ["X.X", "X.X", "XXX", "X.X", "X.X"],
    'I': ["XXX", ".X.", ".X.", ".X.", "XXX"],
    'K': ["X.X", "X.X", "XX.", "X.X", "X.X"],
    'L': ["X..", "X..", "X..", "X..", "XXX"],
    'N': ["X..X", "XX.X", "X.XX", "X..X", "X..X"],
    'O': ["XXX", "X.X", "X.X", "X.X", "XXX"],
    'S': [".XX", "X..", ".X.", "..X", "XX."],
    'U': ["X.X", "X.X", "X.X", "X.X", "XXX"],
    'V': ["X.X", "X.X", "X.X", "X.X", ".X."],
    'W': ["X...X", "X...X", "X.X.X", "X.X.X", ".X.X."],
    '@': [".XXX.", "X...X", "X.XXX", "X.X.X", "X.XXX"],
    ' ': ["..", "..", "..", "..", ".."],
}


def text_width(s, sc=1):
    return sum((len(FONT[ch][0]) + 1) * sc for ch in s) - sc


def draw_text(arr, x, y, s, color, sc=1, alpha=1.0):
    """Blend pixel text into an RGB float/uint8 array."""
    cx = x
    for ch in s:
        g = FONT[ch]
        for r, row in enumerate(g):
            for c, px in enumerate(row):
                if px == 'X':
                    x0, y0 = cx + c * sc, y + r * sc
                    blend_rect(arr, x0, y0, x0 + sc - 1, y0 + sc - 1, color, alpha)
        cx += (len(g[0]) + 1) * sc


def blend_rect(arr, x0, y0, x1, y1, color, alpha):
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(W - 1, x1), min(H - 1, y1)
    if x1 < x0 or y1 < y0:
        return
    region = arr[y0:y1 + 1, x0:x1 + 1].astype(np.float32)
    col = np.array(color, np.float32)
    arr[y0:y1 + 1, x0:x1 + 1] = (region * (1 - alpha) + col * alpha).astype(arr.dtype)


HEADPHONES = [
    "..XXXXXXX..",
    ".X.......X.",
    "X.........X",
    "X.........X",
    "XX.......XX",
    "XXX.....XXX",
    "XXX.....XXX",
    ".X.......X.",
]


def draw_bitmap(arr, x, y, rows, color, alpha=1.0, sc=1):
    for r, row in enumerate(rows):
        for c, px in enumerate(row):
            if px == 'X':
                blend_rect(arr, x + c * sc, y + r * sc, x + c * sc + sc - 1, y + r * sc + sc - 1, color, alpha)


# ----------------------------------------------------------------------------
# Static scene: the village inside the globe
# ----------------------------------------------------------------------------
SKY_TOP = (14, 20, 62)
SKY_HOR = (54, 64, 122)
SNOW = (238, 242, 252)
SNOW_SHADE = (204, 214, 238)
SNOW_DEEP = (180, 194, 226)
UNLIT = (44, 50, 84)
LIT = (255, 214, 118)
LIT_TOP = (255, 238, 176)
FRAME = (34, 30, 48)

WINDOWS = []       # (x0, y0, x1, y1) inclusive, in lighting order
TOWER_WINDOWS = []


def ground_y(x):
    return 197 + 12 * ((x - GCX) / GRX) ** 2


def build_scene():
    yy, xx = np.mgrid[0:H, 0:W]
    arr = np.zeros((H, W, 3), np.uint8)
    # sky gradient
    tt = np.clip((yy - 40) / 135.0, 0, 1)[..., None]
    sky = (np.array(SKY_TOP) * (1 - tt) + np.array(SKY_HOR) * tt)
    arr[:] = sky.astype(np.uint8)

    img = Image.fromarray(arr)
    sol = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(img)
    dm = ImageDraw.Draw(sol)

    def rect(x0, y0, x1, y1, c, s=True):
        d.rectangle([x0, y0, x1, y1], fill=c)
        if s:
            dm.rectangle([x0, y0, x1, y1], fill=255)

    def poly(pts, c, s=True):
        d.polygon(pts, fill=c)
        if s:
            dm.polygon(pts, fill=255)

    def hline(x0, x1, y, c):
        d.line([x0, y, x1, y], fill=c)

    # far hills (snowy, dim)
    far = [(x, 172 + 7 * math.sin((x - 10) / 23.0) + 4 * math.sin(x / 9.0)) for x in range(0, W + 1, 2)]
    poly([(0, 230)] + far + [(W, 230)], (74, 86, 138), s=False)
    near = [(x, 182 + 6 * math.sin((x + 40) / 19.0)) for x in range(0, W + 1, 2)]
    poly([(0, 230)] + near + [(W, 230)], (96, 110, 160), s=False)
    # distant pines on hills
    for px, base, h in [(22, 183, 12), (30, 181, 9), (150, 180, 11), (160, 184, 8), (112, 176, 10)]:
        poly([(px, base - h), (px - 4, base), (px + 4, base)], (48, 62, 108), s=False)

    # --- helper to draw a house: walls + roof + snow cap
    def house(x0, x1, ytop, ybot, wall, roof, peak_dy, dark=None):
        rect(x0, ytop, x1, ybot, wall)
        if dark:
            rect(x1 - 3, ytop, x1, ybot, dark)   # shaded side
        px = (x0 + x1) // 2
        poly([(x0 - 2, ytop), (px, ytop - peak_dy), (x1 + 2, ytop)], roof)
        # snow on roof: two thick slanted lines
        d.line([(x0 - 2, ytop), (px, ytop - peak_dy)], fill=SNOW, width=2)
        d.line([(px, ytop - peak_dy), (x1 + 2, ytop)], fill=SNOW, width=2)
        dm.line([(x0 - 2, ytop), (px, ytop - peak_dy)], fill=255, width=2)
        dm.line([(px, ytop - peak_dy), (x1 + 2, ytop)], fill=255, width=2)
        return px

    def window(x0, y0, w, h, lst=WINDOWS):
        rect(x0 - 1, y0 - 1, x0 + w, y0 + h, FRAME)
        rect(x0, y0, x0 + w - 1, y0 + h - 1, UNLIT)
        lst.append((x0, y0, x0 + w - 1, y0 + h - 1))

    def door(x0, y0, w, h, c=(70, 44, 38)):
        rect(x0, y0, x0 + w - 1, y0 + h - 1, c)
        rect(x0 + w - 2, y0 + h // 2, x0 + w - 2, y0 + h // 2, (214, 182, 90))

    def chimney(x, ytop, h):
        rect(x, ytop, x + 2, ytop + h, (92, 70, 66))
        rect(x - 1, ytop - 1, x + 3, ytop, SNOW)

    # --- back row --------------------------------------------------------
    # back-left small house (behind the cottage)
    house(30, 50, 150, 172, (160, 170, 196), (62, 70, 104), 14, dark=(128, 138, 168))
    # back-right two-storey house
    house(118, 150, 130, 168, (214, 196, 170), (110, 58, 56), 16, dark=(182, 164, 140))
    chimney(141, 120, 10)

    # --- clock tower (centre-right) --------------------------------------
    TX0, TX1 = 86, 104
    rect(TX0, 100, TX1, 198, (170, 178, 204))
    rect(TX1 - 4, 100, TX1, 198, (134, 142, 172))
    hline(TX0, TX1, 150, (134, 142, 172))
    hline(TX0, TX1, 170, (134, 142, 172))
    # spire
    poly([(TX0 - 2, 100), (95, 80), (TX1 + 2, 100)], (70, 56, 84))
    d.line([(TX0 - 2, 100), (95, 80)], fill=SNOW, width=2)
    d.line([(95, 80), (TX1 + 2, 100)], fill=SNOW, width=2)
    dm.polygon([(TX0 - 2, 100), (95, 80), (TX1 + 2, 100)], fill=255)
    rect(94, 72, 96, 80, (200, 170, 90))           # finial
    rect(93, 72, 97, 73, (200, 170, 90))
    # clock face (unlit)
    d.ellipse([88, 112, 102, 126], fill=(206, 198, 176), outline=(60, 50, 70))
    dm.ellipse([88, 112, 102, 126], fill=255)
    d.line([(95, 119), (95, 114)], fill=(50, 40, 60))
    d.line([(95, 119), (99, 119)], fill=(50, 40, 60))
    # bell window + tower windows
    rect(92, 134, 98, 144, (40, 36, 60))
    rect(93, 135, 97, 143, (30, 26, 48))
    TOWER_WINDOWS.append((93, 135, 97, 143))
    rect(93, 156, 97, 163, FRAME)
    rect(94, 157, 96, 162, UNLIT)
    TOWER_WINDOWS.append((94, 157, 96, 162))
    rect(93, 176, 97, 183, FRAME)
    rect(94, 177, 96, 182, UNLIT)
    TOWER_WINDOWS.append((94, 177, 96, 182))
    door(92, 188, 7, 11, (60, 44, 60))

    # --- middle row -------------------------------------------------------
    # left tall house (two storeys)
    house(52, 80, 150, 198, (196, 150, 120), (50, 88, 96), 18, dark=(164, 124, 100))
    chimney(74, 139, 9)
    # right bakery
    house(108, 146, 164, 198, (214, 196, 170), (110, 58, 56), 16, dark=(182, 164, 140))
    rect(110, 170, 144, 171, (150, 90, 70))        # awning stripe
    rect(110, 172, 144, 172, (200, 120, 90))

    # --- front row --------------------------------------------------------
    # left cottage
    house(24, 50, 172, 198, (150, 160, 190), (110, 58, 56), 14, dark=(124, 134, 164))
    chimney(44, 162, 9)
    # far-right cottage
    house(148, 166, 176, 198, (196, 150, 120), (62, 70, 104), 12, dark=(164, 124, 100))

    # --- windows in lighting order (12) -----------------------------------
    window(114, 180, 12, 8)      # 1  bakery wide window
    window(56, 158, 7, 7)        # 2  tall house upper-left
    window(139, 140, 7, 7)       # 3  back-right upper-right
    window(29, 180, 6, 7)        # 4  cottage left
    window(132, 178, 7, 8)       # 5  bakery right
    window(56, 178, 7, 7)        # 6  tall house lower-left
    window(35, 156, 6, 6)        # 7  back-left house
    window(124, 140, 7, 7)       # 8  back-right upper-left
    window(44, 180, 6, 7)        # 9  cottage right
    window(69, 158, 7, 7)        # 10 tall house upper-right
    window(153, 184, 6, 6)       # 11 far-right cottage
    window(68, 177, 9, 8)        # 12 tall house shop window
    door(36, 188, 6, 10)
    door(124, 188, 7, 10)

    # --- trees inside the globe ------------------------------------------
    def pine(px, base, h, c1=(36, 72, 70), c2=(52, 96, 88)):
        # three stacked triangles
        poly([(px, base - h), (px - 4, base - h + 7), (px + 4, base - h + 7)], c2)
        poly([(px, base - h + 4), (px - 6, base - h + 13), (px + 6, base - h + 13)], c1)
        poly([(px, base - h + 9), (px - 7, base), (px + 7, base)], c2)
        d.line([(px - 4, base - h + 7), (px, base - h)], fill=SNOW)
        d.line([(px - 6, base - h + 13), (px, base - h + 4)], fill=SNOW)
        rect(px, base, px, base + 3, (70, 50, 40))

    pine(16, 196, 22)
    pine(170, 196, 20)
    pine(156, 172, 14)

    # --- lamp post --------------------------------------------------------
    rect(83, 178, 83, 199, (30, 28, 40))
    rect(81, 172, 85, 177, (30, 28, 40))
    rect(82, 173, 84, 176, (255, 220, 140))
    rect(82, 171, 84, 171, SNOW)

    # --- ground: snow mound ------------------------------------------------
    gpts = [(x, ground_y(x)) for x in range(0, W + 1, 2)]
    poly([(0, H)] + gpts + [(W, H)], SNOW)
    gpts2 = [(x, ground_y(x) + 14 + 2 * math.sin(x / 7.0)) for x in range(0, W + 1, 2)]
    poly([(0, H)] + gpts2 + [(W, H)], SNOW_SHADE)
    gpts3 = [(x, ground_y(x) + 26 + 2 * math.sin(x / 5.0)) for x in range(0, W + 1, 2)]
    poly([(0, H)] + gpts3 + [(W, H)], SNOW_DEEP)
    # cobble path
    for i in range(16):
        x = 60 + i * 4 + (i % 2) * 2
        y = 200 + (i % 3)
        rect(x, y, x + 2, y + 1, (120, 130, 160))
    # a few snow sparkles on the ground
    for _ in range(26):
        x = rng.randint(GCX - 60, GCX + 60)
        y = int(ground_y(x)) + rng.randint(2, 20)
        d.point((x, y), fill=(255, 255, 255))
    # tiny snowman (left of the path)
    d.ellipse([38, 204, 44, 210], fill=SNOW, outline=SNOW_SHADE)
    d.ellipse([39, 200, 43, 204], fill=SNOW, outline=SNOW_SHADE)
    d.point((40, 202), fill=(20, 20, 30)); d.point((42, 202), fill=(20, 20, 30))
    d.point((41, 203), fill=(230, 120, 60))
    dm.ellipse([38, 200, 44, 210], fill=255)

    return np.array(img), np.array(sol) > 0


SCENE, SOLID = build_scene()

# landing surface per column (top-most solid pixel), used by the snow
SURF = np.full(W, H, np.int32)
for x in range(W):
    col = np.nonzero(SOLID[:, x])[0]
    SURF[x] = col[0] if len(col) else int(ground_y(x))
SURF_F = SURF.astype(np.float32)

# stars (static positions, twinkle at render time)
STARS = []
for _ in range(90):
    x = rng.randint(GCX - GRX + 6, GCX + GRX - 6)
    y = rng.randint(GCY - GRY + 6, 168)
    if ((x - GCX) / GRX) ** 2 + ((y - GCY) / GRY) ** 2 < 0.9 and not SOLID[y, x] and y < 165 + 0:
        STARS.append((x, y, rng.random() * 6.28, rng.choice([0.6, 0.8, 1.0])))

# globe masks
yy, xx = np.mgrid[0:H, 0:W]
RAD = ((xx - GCX) / GRX) ** 2 + ((yy - GCY) / GRY) ** 2
INSIDE = RAD <= 1.0
# sky area shows what's behind the glass (the cat) faintly
SKY_AREA = INSIDE & ~SOLID & (yy < ground_y(GCX) + 0) & (yy < 182)
GLASS_ALPHA = np.where(SKY_AREA, 0.72, 1.0).astype(np.float32)
GLASS_ALPHA[~INSIDE] = 0.0
# vignette near the rim
VIG = (1.0 - 0.35 * np.clip((np.sqrt(RAD) - 0.78) / 0.22, 0, 1)).astype(np.float32)[..., None]
# glass highlight: thin arc at the upper-left
ang = np.arctan2((yy - GCY) / GRY, (xx - GCX) / GRX)
r = np.sqrt(RAD)
HIGHLIGHT = ((r > 0.90) & (r < 0.95) & (ang > -2.55) & (ang < -1.75)).astype(np.float32) * 0.55
HIGHLIGHT += ((r > 0.86) & (r < 0.89) & (ang > -2.35) & (ang < -2.05)).astype(np.float32) * 0.35
RIM = ((r > 0.985) & (r < 1.03))
RIM_OUT = ((r > 1.03) & (r < 1.06))


def glow_patch(radius):
    g = np.mgrid[-radius:radius + 1, -radius:radius + 1]
    dd = np.sqrt(g[0] ** 2 + g[1] ** 2) / radius
    return np.clip(1 - dd, 0, 1) ** 2


GLOW_S = glow_patch(9)
GLOW_M = glow_patch(14)
GLOW_L = glow_patch(30)


def add_glow(fimg, cx, cy, patch, color, k):
    rad = patch.shape[0] // 2
    x0, y0 = cx - rad, cy - rad
    x1, y1 = cx + rad + 1, cy + rad + 1
    px0, py0 = max(0, -x0), max(0, -y0)
    px1 = patch.shape[1] - max(0, x1 - W)
    py1 = patch.shape[0] - max(0, y1 - H)
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if x1 <= x0 or y1 <= y0:
        return
    p = patch[py0:py1, px0:px1][..., None] * k
    fimg[y0:y1, x0:x1] += p * np.array(color, np.float32)


# ----------------------------------------------------------------------------
# Background: table, globe base, cat
# ----------------------------------------------------------------------------
def build_background():
    yy, xx = np.mgrid[0:H, 0:W]
    t = (yy / H)[..., None]
    bg = (np.array((16, 20, 44)) * (1 - t) + np.array((5, 6, 18)) * t)
    # soft vignette
    dx = (xx - W / 2) / (W / 2)
    dy = (yy - H / 2) / (H / 2)
    v = 1 - 0.35 * np.clip(dx ** 2 + dy ** 2 - 0.3, 0, 1)
    bg = bg * v[..., None]
    # table top
    tab = yy >= BASE_BOT - 4
    bg[tab] = np.array((20, 20, 40))
    # table edge highlight
    bg[BASE_BOT - 4] = np.array((44, 46, 78))
    # soft reflection under the base
    rr = ((xx - GCX) / 70.0) ** 2 + ((yy - (BASE_BOT + 12)) / 10.0) ** 2
    refl = np.clip(1 - rr, 0, 1)[..., None] * 0.35
    bg = bg + refl * np.array((60, 62, 110))
    return bg.astype(np.float32)


BG = build_background()


def base_layer():
    """Globe base as an RGBA numpy layer (drawn once)."""
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    top_w, bot_w = 60, 70
    d.polygon([(GCX - top_w, BASE_TOP), (GCX + top_w, BASE_TOP),
               (GCX + bot_w, BASE_BOT), (GCX - bot_w, BASE_BOT)], fill=(74, 46, 36, 255))
    # gold band and lip
    d.rectangle([GCX - top_w - 2, BASE_TOP - 3, GCX + top_w + 2, BASE_TOP], fill=(196, 156, 76, 255))
    d.rectangle([GCX - top_w - 2, BASE_TOP - 3, GCX + top_w + 2, BASE_TOP - 3], fill=(236, 206, 120, 255))
    d.rectangle([GCX - bot_w, BASE_BOT - 4, GCX + bot_w, BASE_BOT - 2], fill=(196, 156, 76, 255))
    d.rectangle([GCX - bot_w, BASE_BOT - 1, GCX + bot_w, BASE_BOT], fill=(40, 24, 20, 255))
    # plaque
    d.rectangle([GCX - 18, BASE_TOP + 10, GCX + 18, BASE_TOP + 20], fill=(196, 156, 76, 255))
    d.rectangle([GCX - 16, BASE_TOP + 12, GCX + 16, BASE_TOP + 18], fill=(120, 86, 40, 255))
    for i in range(5):
        d.line([(GCX - 13 + i * 6, BASE_TOP + 15), (GCX - 10 + i * 6, BASE_TOP + 15)], fill=(220, 190, 110, 255))
    # wood grain
    for i in range(6):
        y = BASE_TOP + 4 + i * 5
        d.line([(GCX - top_w + 4 + i, y), (GCX + top_w - 4 - i, y)], fill=(86, 54, 42, 255))
        d.line([(GCX - top_w + 4 + i, y + 1), (GCX + top_w - 4 - i, y + 1)], fill=(64, 40, 32, 255))
    return np.array(img).astype(np.float32)


BASE = base_layer()


def draw_cat(bg, t):
    """Draw an original cat (grey tabby, green eyes) behind the globe on the left."""
    if t < T_CAT:
        return bg
    img = Image.fromarray(bg.clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    slide = smooth((t - T_CAT) / 2.2)
    cx = int(lerp(-90, 44, slide))      # head centre x
    cy = 100
    fur = (60, 62, 74)
    fur_d = (44, 46, 56)
    fur_l = (84, 86, 100)
    # body (huge, mostly off-frame) and head
    d.ellipse([cx - 90, cy + 40, cx + 70, cy + 230], fill=fur)
    d.ellipse([cx - 54, cy - 46, cx + 54, cy + 50], fill=fur)
    # ears
    d.polygon([(cx - 50, cy - 20), (cx - 44, cy - 72), (cx - 12, cy - 40)], fill=fur)
    d.polygon([(cx + 50, cy - 20), (cx + 44, cy - 72), (cx + 12, cy - 40)], fill=fur)
    d.polygon([(cx - 44, cy - 26), (cx - 40, cy - 60), (cx - 20, cy - 38)], fill=(120, 80, 90))
    d.polygon([(cx + 44, cy - 26), (cx + 40, cy - 60), (cx + 20, cy - 38)], fill=(120, 80, 90))
    # tabby stripes on the forehead
    for i, dx in enumerate([-16, -6, 6, 16]):
        d.line([(cx + dx, cy - 44), (cx + dx // 2, cy - 14)], fill=fur_d, width=3)
    # cheeks lighter
    d.ellipse([cx - 40, cy + 6, cx - 4, cy + 40], fill=fur_l)
    d.ellipse([cx + 4, cy + 6, cx + 40, cy + 40], fill=fur_l)
    # eyes
    open_amt = smooth((t - T_EYES) / 0.35)
    if T_BLINK <= t < T_BLINK + 0.36:
        b = (t - T_BLINK) / 0.36
        open_amt *= 1 - math.sin(b * math.pi)
    eh = int(round(12 * open_amt))
    for ex in (cx - 22, cx + 22):
        if eh >= 2:
            d.ellipse([ex - 12, cy - eh, ex + 12, cy + eh], fill=(128, 206, 92))
            d.ellipse([ex - 12, cy - eh, ex + 12, cy + eh // 2], fill=(150, 226, 110))
            pw = 3 if t > T_PAW else 5
            d.rectangle([ex - pw // 2, cy - eh + 2, ex + pw // 2, cy + eh - 2], fill=(10, 14, 18))
            d.rectangle([ex - 7, cy - eh + 3, ex - 5, cy - eh + 5], fill=(255, 255, 255))
        else:
            d.line([(ex - 12, cy), (ex + 12, cy)], fill=fur_d, width=2)
    # nose and mouth
    d.polygon([(cx - 4, cy + 18), (cx + 4, cy + 18), (cx, cy + 23)], fill=(220, 140, 150))
    d.line([(cx, cy + 23), (cx, cy + 27)], fill=fur_d)
    d.line([(cx - 6, cy + 30), (cx, cy + 27), (cx + 6, cy + 30)], fill=fur_d)
    # whiskers
    for dy in (-2, 4, 10):
        d.line([(cx - 30, cy + 22 + dy), (cx - 62, cy + 18 + dy * 2)], fill=(150, 150, 160))
        d.line([(cx + 30, cy + 22 + dy), (cx + 62, cy + 18 + dy * 2)], fill=(150, 150, 160))
    return np.array(img).astype(np.float32)


# ----------------------------------------------------------------------------
# Snow particle system
# ----------------------------------------------------------------------------
class Snow:
    def __init__(self):
        self.x = np.zeros(0, np.float32)
        self.y = np.zeros(0, np.float32)
        self.vx = np.zeros(0, np.float32)
        self.vy = np.zeros(0, np.float32)
        self.big = np.zeros(0, bool)
        self.rs = np.random.RandomState(11)
        # initial "just shaken" cloud
        self.spawn(420, swirl=True)

    def spawn(self, n, swirl=False, burst=False):
        rs = self.rs
        if burst:
            x = rs.uniform(GCX - 60, GCX + 60, n)
            y = SURF_F[np.clip(x.astype(int), 0, W - 1)] - rs.uniform(0, 6, n)
            vx = rs.uniform(-30, 30, n)
            vy = rs.uniform(-70, -15, n)
        elif swirl:
            ang = rs.uniform(0, 6.28, n)
            rad = np.sqrt(rs.uniform(0, 1, n))
            x = GCX + np.cos(ang) * rad * (GRX - 4)
            y = GCY + np.sin(ang) * rad * (GRY - 4)
            vx = rs.uniform(-25, 25, n)
            vy = rs.uniform(-10, 20, n)
        else:
            x = rs.uniform(GCX - GRX + 3, GCX + GRX - 3, n)
            y = np.full(n, GCY - GRY + 2.0) + rs.uniform(0, 6, n)
            vx = rs.uniform(-6, 6, n)
            vy = rs.uniform(8, 16, n)
        keep = ((x - GCX) / GRX) ** 2 + ((y - GCY) / GRY) ** 2 < 0.97
        self.x = np.concatenate([self.x, x[keep].astype(np.float32)])
        self.y = np.concatenate([self.y, y[keep].astype(np.float32)])
        self.vx = np.concatenate([self.vx, vx[keep].astype(np.float32)])
        self.vy = np.concatenate([self.vy, vy[keep].astype(np.float32)])
        self.big = np.concatenate([self.big, rs.uniform(0, 1, keep.sum()) < 0.12])

    def step(self, t, dt, cap):
        n = len(self.x)
        if n == 0:
            return
        # drift and settling
        wind = 5 * math.sin(t * 0.6) * np.ones(n)
        swirl = 3 * np.sin(self.y * 0.08 + t * 1.3)
        term = np.where(self.big, 15.0, 11.0)
        self.vy += (term - self.vy) * dt * 1.4
        self.vx += ((wind + swirl) - self.vx) * dt * 0.9
        self.x += self.vx * dt
        self.y += self.vy * dt
        # bounce softly off the glass
        rr = ((self.x - GCX) / GRX) ** 2 + ((self.y - GCY) / GRY) ** 2
        out = rr > 0.96
        if out.any():
            nx = (self.x[out] - GCX) / GRX
            ny = (self.y[out] - GCY) / GRY
            nrm = np.sqrt(nx * nx + ny * ny) + 1e-6
            self.x[out] = GCX + nx / nrm * 0.975 * GRX
            self.y[out] = GCY + ny / nrm * 0.975 * GRY
            self.vx[out] *= -0.3
        xi = np.clip(self.x.astype(int), 0, W - 1)
        landed = self.y >= SURF_F[xi] - cap - 0.5
        keep = ~landed
        self.x, self.y, self.vx, self.vy, self.big = (self.x[keep], self.y[keep], self.vx[keep],
                                                     self.vy[keep], self.big[keep])

    def draw(self, img):
        if len(self.x) == 0:
            return
        xi = np.clip(self.x.astype(int), 0, W - 1)
        yi = np.clip(self.y.astype(int), 0, H - 1)
        inside = RAD[yi, xi] < 0.985
        xi, yi, big = xi[inside], yi[inside], self.big[inside]
        img[yi, xi] = np.array((236, 240, 252), np.float32)
        bx, by = xi[big], yi[big]
        img[by, np.clip(bx + 1, 0, W - 1)] = np.array((220, 226, 246), np.float32)
        img[np.clip(by + 1, 0, H - 1), bx] = np.array((220, 226, 246), np.float32)


class Glitter:
    """Twelve special flakes that sparkle and chime when they land."""

    def __init__(self):
        rs = np.random.RandomState(5)
        self.items = []
        for i, tl in enumerate(GLITTER_TIMES):
            x = int(rs.uniform(GCX - 56, GCX + 56))
            ys = SURF[x]
            fall = 3.2
            self.items.append(dict(x=x, y_land=ys, t_spawn=tl - fall, t_land=tl, ph=rs.uniform(0, 6.28)))

    def draw(self, img, fimg, t):
        for it in self.items:
            if t < it['t_spawn'] or t > it['t_land'] + 0.6:
                continue
            if t < it['t_land']:
                u = (t - it['t_spawn']) / (it['t_land'] - it['t_spawn'])
                y = lerp(GCY - GRY + 3, it['y_land'] - 1, u)
                x = it['x'] + 4 * math.sin(t * 2.0 + it['ph'])
                xi, yi = int(x), int(y)
                tw = 0.6 + 0.4 * math.sin(t * 14 + it['ph'])
                c = np.array((255, 255, 255), np.float32)
                for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                    px, py = xi + dx, yi + dy
                    if 0 <= px < W and 0 <= py < H:
                        img[py, px] = c if (dx == 0 and dy == 0) else img[py, px] * (1 - tw) + c * tw
                add_glow(fimg, xi, yi, GLOW_S, (180, 220, 255), 0.35 * tw)
            else:
                u = (t - it['t_land']) / 0.6
                rad = int(2 + 7 * u)
                k = (1 - u) ** 2
                add_glow(fimg, it['x'], it['y_land'] - 1, GLOW_M, (200, 230, 255), 0.9 * k)
                # expanding sparkle ring (4 points)
                for dx, dy in ((rad, 0), (-rad, 0), (0, -rad), (0, rad)):
                    px, py = it['x'] + dx, it['y_land'] - 1 + dy
                    if 0 <= px < W and 0 <= py < H and RAD[py, px] < 0.97:
                        img[py, px] = img[py, px] * (1 - k) + np.array((255, 255, 255), np.float32) * k


# ----------------------------------------------------------------------------
# Frame rendering
# ----------------------------------------------------------------------------
def globe_angle(t):
    if t < T_HIT:
        return 0.0, 0.0
    tau = t - T_HIT
    a = -4.2 * math.sin(2 * math.pi * 1.05 * tau) * math.exp(-1.25 * tau) * smooth(tau / 0.12 + 0.2)
    dx = 1.5 * math.sin(2 * math.pi * 1.05 * tau) * math.exp(-1.3 * tau)
    return a, dx


def render_interior(t, snow, glitter):
    img = SCENE.astype(np.float32).copy()
    fimg = np.zeros_like(img)      # additive glow buffer

    # twinkling stars
    for (x, y, ph, b) in STARS:
        v = b * (0.55 + 0.45 * math.sin(t * 1.7 + ph))
        img[y, x] = np.array((150, 170, 230), np.float32) * (1 - v) + np.array((255, 255, 255), np.float32) * v

    # snow cap growing on the skyline (plus a little stir after the nudge)
    cap = 2.0 * smooth((t - 1.0) / 11.0)
    if t > T_HIT:
        cap -= 1.0 * math.exp(-(t - T_HIT) * 1.2)
    capi = int(round(cap))
    if capi > 0:
        xs = np.arange(GCX - GRX + 2, GCX + GRX - 2)
        for k in range(1, capi + 1):
            ys = SURF[xs] - k
            ok = (ys >= 0) & (RAD[np.clip(ys, 0, H - 1), xs] < 0.98)
            img[ys[ok], xs[ok]] = np.array((244, 247, 255), np.float32)

    # lamp post glow (gently flickering)
    fl = 0.55 + 0.08 * math.sin(t * 9.0) + 0.05 * math.sin(t * 23.0)
    add_glow(fimg, 83, 175, GLOW_M, (255, 200, 110), fl)

    # windows lighting one at a time
    for i, (x0, y0, x1, y1) in enumerate(WINDOWS):
        a = smooth((t - WINDOW_TIMES[i]) / 0.45)
        if a <= 0:
            continue
        flick = 1 - 0.06 * (0.5 + 0.5 * math.sin(t * 7 + i))
        col = np.array(UNLIT, np.float32) * (1 - a) + np.array(LIT, np.float32) * a * flick
        img[y0:y1 + 1, x0:x1 + 1] = col
        img[y0, x0:x1 + 1] = np.array(UNLIT, np.float32) * (1 - a) + np.array(LIT_TOP, np.float32) * a
        # window cross bar
        mx = (x0 + x1) // 2
        img[y0:y1 + 1, mx] = img[y0:y1 + 1, mx] * 0.75
        add_glow(fimg, (x0 + x1) // 2, (y0 + y1) // 2, GLOW_M, (255, 190, 100), 0.55 * a)
        # a bright flash on the note itself
        pulse = max(0.0, 1 - (t - WINDOW_TIMES[i]) / 0.5)
        add_glow(fimg, (x0 + x1) // 2, (y0 + y1) // 2, GLOW_L, (255, 220, 150), 0.25 * pulse * a)

    # clock tower finale
    ca = smooth((t - T_CLOCK) / 0.8)
    if ca > 0:
        face = np.array((255, 236, 160), np.float32)
        yy0, xx0 = np.mgrid[112:127, 88:103]
        m = ((xx0 - 95) ** 2 + (yy0 - 119) ** 2) <= 36
        region = img[112:127, 88:103]
        region[m] = region[m] * (1 - ca) + face * ca
        img[114:119, 95] = img[114:119, 95] * 0.3
        img[119, 95:100] = img[119, 95:100] * 0.3
        for (x0, y0, x1, y1) in TOWER_WINDOWS:
            img[y0:y1 + 1, x0:x1 + 1] = np.array(UNLIT, np.float32) * (1 - ca) + np.array(LIT, np.float32) * ca
        add_glow(fimg, 95, 119, GLOW_L, (255, 210, 130), 0.9 * ca)
        add_glow(fimg, 95, 140, GLOW_M, (255, 200, 120), 0.5 * ca)
        pulse = max(0.0, 1 - (t - T_CLOCK) / 2.5)
        add_glow(fimg, 95, 130, GLOW_L, (255, 230, 170), 0.6 * pulse)
        # the whole village warms a touch
        img += np.array((10, 6, 0), np.float32) * ca

    glitter.draw(img, fimg, t)
    snow.draw(img)

    img = img + fimg
    img *= VIG
    # glass highlight
    img = img * (1 - HIGHLIGHT[..., None]) + np.array((230, 240, 255), np.float32) * HIGHLIGHT[..., None]
    return np.clip(img, 0, 255)


def compose(t, snow, glitter):
    bg = draw_cat(BG, t)
    interior = render_interior(t, snow, glitter)

    # Build the globe + base as one RGBA layer so the whole thing can rock.
    layer = np.zeros((H, W, 4), np.float32)
    layer[..., :3] = interior
    layer[..., 3] = GLASS_ALPHA * 255
    # rim
    layer[RIM, :3] = np.array((130, 160, 220), np.float32)
    layer[RIM, 3] = 230
    layer[RIM_OUT, :3] = np.array((30, 36, 70), np.float32)
    layer[RIM_OUT, 3] = 200
    # base on top
    ba = BASE[..., 3:4] / 255.0
    layer[..., :3] = layer[..., :3] * (1 - ba) + BASE[..., :3] * ba
    layer[..., 3] = np.maximum(layer[..., 3], BASE[..., 3])

    angle, dx = globe_angle(t)
    if abs(angle) > 0.05 or abs(dx) > 0.2:
        im = Image.fromarray(np.clip(layer, 0, 255).astype(np.uint8), 'RGBA')
        im = im.rotate(angle, resample=Image.NEAREST, center=PIVOT, translate=(dx, 0))
        layer = np.array(im).astype(np.float32)

    a = layer[..., 3:4] / 255.0
    out = bg * (1 - a) + layer[..., :3] * a
    out = np.clip(out, 0, 255).astype(np.uint8)

    out = draw_paw(out, t)

    # title card
    t0, t1 = T_TITLE
    if t0 - 0.5 <= t <= t1 + 0.5:
        al = smooth((t - t0 + 0.5) / 0.5) * (1 - smooth((t - t1) / 0.5))
        if al > 0:
            s1 = "SNOW GLOBE"
            w1 = text_width(s1, 2)
            bx0, bx1 = GCX - w1 // 2 - 6, GCX + w1 // 2 + 6
            blend_rect(out, bx0, 22, bx1, 68, (8, 10, 24), 0.85 * al)
            blend_rect(out, bx0, 22, bx1, 22, (120, 140, 200), 0.6 * al)
            blend_rect(out, bx0, 68, bx1, 68, (120, 140, 200), 0.6 * al)
            draw_text(out, GCX - w1 // 2, 27, s1, (250, 250, 255), 2, al)
            s2 = "VILLAGE"
            w2 = text_width(s2, 1)
            draw_text(out, GCX - w2 // 2, 40, s2, (190, 200, 240), 1, al)
            draw_bitmap(out, GCX - 5, 50, HEADPHONES, (250, 250, 255), al)
            blend_rect(out, GCX - 5, 55, GCX - 3, 58, (250, 250, 255), al)
            blend_rect(out, GCX + 3, 55, GCX + 5, 58, (250, 250, 255), al)

    # handle
    if t >= T_HANDLE:
        al = 0.75 * smooth((t - T_HANDLE) / 1.0)
        draw_text(out, 8, H - 18, "@NICKLAUNCHES", (200, 210, 240), 1, al)
    return out


def draw_paw(out, t):
    """The cat's paw comes around the front-left of the globe and taps the glass."""
    if t < T_PAW:
        return out
    reach = smooth((t - T_PAW) / 0.55)
    if t >= T_PAW_BACK:
        reach *= 1 - smooth((t - T_PAW_BACK) / 0.9)
    if reach <= 0:
        return out
    img = Image.fromarray(out)
    d = ImageDraw.Draw(img)
    fur = (60, 62, 74)
    fur_l = (84, 86, 100)
    fur_d = (44, 46, 56)
    px = int(lerp(-30, GCX - GRX + 14, reach))
    py = int(lerp(300, 172, reach))
    d.line([(-40, 330), (px, py)], fill=fur, width=22)
    d.line([(-40, 330), (px, py)], fill=fur_d, width=4)
    d.ellipse([px - 13, py - 10, px + 13, py + 12], fill=fur_l)
    d.ellipse([px - 13, py - 10, px + 13, py + 12], outline=fur)
    for i, dx in enumerate([-8, -3, 3, 8]):
        ty = py - 11 + (0 if i in (1, 2) else 2)
        d.ellipse([px + dx - 3, ty - 2, px + dx + 3, ty + 5], fill=fur_l, outline=fur)
    # paw pad hint (we see the side of the paw)
    d.ellipse([px - 4, py + 2, px + 4, py + 8], fill=(160, 120, 130))
    return np.array(img)


def upscale(frame):
    return np.repeat(np.repeat(frame, SCALE, axis=0), SCALE, axis=1)


# ----------------------------------------------------------------------------
# Audio synthesis
# ----------------------------------------------------------------------------
def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def synth_audio(path):
    n = int(DUR * SR)
    L = np.zeros(n, np.float64)
    R = np.zeros(n, np.float64)

    def add(sig, t0, pan=0.0):
        i0 = int(t0 * SR)
        i1 = min(n, i0 + len(sig))
        if i1 <= i0:
            return
        s = sig[:i1 - i0]
        gl = math.sqrt(0.5 * (1 - pan))
        gr = math.sqrt(0.5 * (1 + pan))
        L[i0:i1] += s * gl
        R[i0:i1] += s * gr

    def music_box(f, dur=2.6, amp=0.22):
        t = np.arange(int(dur * SR)) / SR
        env = np.minimum(1, t / 0.004)
        s = (np.sin(2 * np.pi * f * t) * np.exp(-t / 1.1)
             + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.45)
             + 0.12 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t / 0.25)
             + 0.05 * np.sin(2 * np.pi * 5.1 * f * t) * np.exp(-t / 0.12))
        return s * env * amp

    def chime(f, dur=1.2, amp=0.045):
        t = np.arange(int(dur * SR)) / SR
        s = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.35)
             + 0.4 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / 0.12))
        return s * np.minimum(1, t / 0.002) * amp

    def warm(f, dur=7.0, amp=0.07, attack=0.3):
        t = np.arange(int(dur * SR)) / SR
        env = np.minimum(1, t / attack) * np.exp(-np.maximum(0, t - attack) / 2.8)
        s = (np.sin(2 * np.pi * f * t)
             + 0.25 * np.sin(2 * np.pi * 2 * f * t)
             + 0.11 * np.sin(2 * np.pi * 3 * f * t)
             + 0.04 * np.sin(2 * np.pi * 4 * f * t))
        vib = 1 + 0.004 * np.sin(2 * np.pi * 5 * t)
        return s * env * amp * vib

    # melody: one note per window, panned by window position
    for i, (m, tw) in enumerate(zip(MELODY, WINDOW_TIMES)):
        x0, _, x1, _ = WINDOWS[i]
        pan = ((x0 + x1) / 2 - GCX) / GRX * 0.6
        add(music_box(midi_hz(m)), tw, pan)
        # a soft octave-below echo for warmth
        add(music_box(midi_hz(m - 12), amp=0.05), tw + 0.01, -pan * 0.5)

    # chimes for the glittering flakes
    for f, tg in zip(CHIME_HZ, GLITTER_TIMES):
        add(chime(f), tg, rng.uniform(-0.5, 0.5))

    # final warm chord when the clock tower lights (G major, comes home)
    for j, m in enumerate([43, 55, 59, 62, 67, 71, 74]):
        add(warm(midi_hz(m), amp=0.075 if m > 50 else 0.09, attack=0.25 + 0.05 * j), T_CLOCK + 0.02 * j, (j - 3) * 0.1)
    add(music_box(midi_hz(79), dur=3.0, amp=0.12), T_CLOCK + 0.05, 0.0)

    # pad: a soft drone that breathes
    t = np.arange(n) / SR
    pad_env = np.minimum(1, t / 8.0) * (1 - np.clip((t - 36.5) / 3.5, 0, 1))
    pad = np.zeros(n)
    for f, a in [(98.0, 1.0), (98.3, 0.8), (147.0, 0.7), (196.0, 0.5), (196.4, 0.4), (247.0, 0.3)]:
        pad += a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28))
    pad *= 0.028 * pad_env * (0.85 + 0.15 * np.sin(2 * np.pi * 0.09 * t))
    L += pad
    R += pad * 0.95

    # snowy hush (filtered noise), louder while the globe is still "shaken"
    noise = np.random.RandomState(3).normal(0, 1, n)
    k = 48
    hush = np.convolve(noise, np.ones(k) / k, mode='same')
    hush_env = 0.05 * np.exp(-t / 2.5) + 0.010
    hush_env *= (1 - np.clip((t - 38.0) / 2.0, 0, 1))
    # a second swirl after the nudge
    hush_env += 0.045 * np.exp(-np.maximum(0, t - T_HIT) / 1.2) * (t >= T_HIT)
    L += hush * hush_env
    R += np.roll(hush, 700) * hush_env

    # the cat taps the glass
    tt = np.arange(int(0.6 * SR)) / SR
    tap = (np.sin(2 * np.pi * 1850 * tt) * np.exp(-tt / 0.045) * 0.16
           + np.sin(2 * np.pi * 920 * tt) * np.exp(-tt / 0.09) * 0.10
           + np.random.RandomState(9).normal(0, 1, len(tt)) * np.exp(-tt / 0.006) * 0.12)
    add(tap, T_HIT, -0.4)
    # faint purr while the cat watches
    pt = np.arange(int(3.6 * SR)) / SR
    purr = np.random.RandomState(4).normal(0, 1, len(pt))
    purr = np.convolve(purr, np.ones(160) / 160, mode='same')
    purr *= (0.5 + 0.5 * np.sin(2 * np.pi * 26 * pt)) * np.minimum(1, pt / 0.6) * (1 - np.clip((pt - 2.8) / 0.8, 0, 1))
    add(purr * 0.09, T_HIT + 0.9, -0.5)

    # simple reverb: convolve with a decaying noise tail
    rt = np.arange(int(1.2 * SR)) / SR
    ir = np.random.RandomState(8).normal(0, 1, len(rt)) * np.exp(-rt / 0.33)
    ir[0] = 0
    ir /= np.sqrt((ir ** 2).sum())

    def reverb(x, mix=0.22):
        y = np.fft.irfft(np.fft.rfft(x, n * 2) * np.fft.rfft(ir, n * 2))[:n]
        return x + mix * y

    L = reverb(L)
    R = reverb(R)

    # master: gentle fades and normalisation
    fade = np.minimum(1, t / 0.15) * np.minimum(1, (DUR - t) / 1.5)
    L *= fade
    R *= fade
    peak = max(np.abs(L).max(), np.abs(R).max(), 1e-6)
    g = 0.71 / peak
    data = np.stack([L * g, R * g], axis=1)
    data = (np.clip(data, -1, 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(data.tobytes())


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def simulate_frames(callback, until=DUR):
    snow = Snow()
    glitter = Glitter()
    dt = 1.0 / FPS
    acc = 0.0
    burst_done = False
    for f in range(int(until * FPS) + 1):
        t = f / FPS
        rate = 6 + 95 * math.exp(-t / 2.6)
        if t > 30:
            rate = 3
        acc += rate * dt
        if acc >= 1:
            k = int(acc)
            acc -= k
            snow.spawn(k)
        if t >= T_HIT and not burst_done:
            snow.spawn(170, burst=True)
            burst_done = True
        cap = 2.0 * smooth((t - 1.0) / 11.0)
        snow.step(t, dt, cap)
        callback(f, t, snow, glitter)


def main():
    args = sys.argv[1:]
    out_dir = os.path.dirname(os.path.abspath(__file__))
    if args and args[0] == '--preview':
        secs = [float(s) for s in args[1].split(',')]
        want = {int(round(s * FPS)) for s in secs}
        pdir = args[2] if len(args) > 2 else os.path.join(out_dir, 'preview')
        os.makedirs(pdir, exist_ok=True)

        def cb(f, t, snow, glitter):
            if f in want:
                fr = compose(t, snow, glitter)
                Image.fromarray(upscale(fr)).resize((540, 960), Image.NEAREST).save(
                    os.path.join(pdir, 'frame_%05.2f.png' % t))
                print('preview', t)
        simulate_frames(cb, until=max(secs))
        return

    out = args[0] if args else os.path.join(out_dir, 'snow_globe_village.mp4')
    wav = os.path.join(os.path.dirname(os.path.abspath(out)) or '.', '.snow_globe_audio.wav')
    print('synthesising audio ...')
    synth_audio(wav)
    print('rendering %d frames ...' % NF)
    cmd = ['ffmpeg', '-y', '-loglevel', 'error',
           '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W * SCALE, H * SCALE), '-r', str(FPS), '-i', '-',
           '-i', wav,
           '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p', '-tune', 'animation',
           '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def cb(f, t, snow, glitter):
        if f >= NF:
            return
        fr = compose(t, snow, glitter)
        p.stdin.write(upscale(fr).tobytes())
        if f % 300 == 0:
            print('  frame %d / %d (t=%.1fs)' % (f, NF, t))
    simulate_frames(cb)
    p.stdin.close()
    p.wait()
    os.remove(wav)
    print('wrote', out)


if __name__ == '__main__':
    main()
