"""Pixel art drawn by code (the 'every pixel is a decision' approach).
Claude writes drawing code; Pillow places pixels; output is deterministic and re-renderable.
Run:  python3 -I gen_sprites.py out
"""
from PIL import Image, ImageDraw
import sys, os, colorsys, random

out = sys.argv[1] if len(sys.argv) > 1 else 'out'; os.makedirs(out, exist_ok=True)

# ---- palette: hue-shifted ramps (shadows go cooler/darker, highlights warmer/lighter)
def ramp(hex_base, steps=5, hue_shift=-0.04):
    r, g, b = [int(hex_base[i:i+2], 16) / 255 for i in (1, 3, 5)]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    cols = []
    for i in range(steps):
        t = (i - steps // 2) / (steps // 2)          # -1 .. 1
        hh = (h + hue_shift * t) % 1.0
        ll = max(0.05, min(0.95, l + 0.16 * t))
        rr, gg, bb = colorsys.hls_to_rgb(hh, ll, min(1, s + 0.1 * abs(t)))
        cols.append((int(rr * 255), int(gg * 255), int(bb * 255), 255))
    return cols
STONE = ramp('#5a6b8c'); MOSS = ramp('#4f8a4a'); WOOD = ramp('#8a5a3a'); FIRE = ramp('#ffb13d', hue_shift=0.06)
ARMOR = ramp('#7fb7ff'); SKIN = ramp('#f2c9a0'); CLOTH = ramp('#d6465a'); SLIME = ramp('#8be04a')
BLACK = (18, 20, 32, 255); T = (0, 0, 0, 0)

def px(img, x, y, c):
    if 0 <= x < img.width and 0 <= y < img.height: img.putpixel((x, y), c)
def rect(img, x, y, w, h, c):
    for yy in range(y, y + h):
        for xx in range(x, x + w): px(img, xx, yy, c)
def dither(img, x, y, w, h, a, b):            # 2x2 Bayer checker between two colours
    for yy in range(y, y + h):
        for xx in range(x, x + w): px(img, xx, yy, a if (xx + yy) % 2 == 0 else b)
def outline(img, c):                            # selective outline: only where a pixel borders transparency
    src = img.copy()
    for y in range(img.height):
        for x in range(img.width):
            if src.getpixel((x, y))[3] == 0: continue
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < img.width and 0 <= ny < img.height) or src.getpixel((nx, ny))[3] == 0:
                    px(img, x, y, c); break

# ---- 16x16 tiles
def tile_floor(seed):
    im = Image.new('RGBA', (16, 16), STONE[2]); rnd = random.Random(seed)
    for _ in range(14): px(im, rnd.randrange(16), rnd.randrange(16), STONE[1])
    for _ in range(6): px(im, rnd.randrange(16), rnd.randrange(16), STONE[3])
    for x in range(16): px(im, x, 15, STONE[0])                    # grout line
    for y in range(16): px(im, 15, y, STONE[0])
    if seed % 3 == 0: rect(im, 3, 9, 4, 2, MOSS[2]); px(im, 7, 10, MOSS[3])
    return im
def tile_wall():
    im = Image.new('RGBA', (16, 16), STONE[1])
    for row in range(4):                                             # brick courses, offset every other row
        off = 4 if row % 2 else 0
        for bx in range(-1, 3):
            x = bx * 8 + off
            rect(im, x, row * 4, 7, 3, STONE[2]); rect(im, x, row * 4, 7, 1, STONE[3])
    for x in range(16): px(im, x, 0, STONE[3])
    return im
def tile_torch(frame):
    im = Image.new('RGBA', (16, 16), T)
    rect(im, 7, 8, 2, 7, WOOD[2]); px(im, 7, 8, WOOD[3])
    f = [(7,6),(8,6),(7,5),(8,5),(7,4)] if frame % 2 == 0 else [(7,6),(8,6),(8,5),(7,5),(8,4),(7,3)]
    for i, (x, y) in enumerate(f): px(im, x, y, FIRE[4] if i < 2 else FIRE[3])
    px(im, 7 if frame % 2 else 8, 7, FIRE[2])
    return im

# ---- original hero: 16x24, 4-frame walk. Body is a template; motion comes from parameters, not copied pixels.
def hero(frame):
    im = Image.new('RGBA', (16, 24), T)
    bob = 1 if frame % 2 else 0
    # legs (alternate)
    la, lb = (0, 2) if frame % 4 in (0, 2) else ((-2, 1) if frame % 4 == 1 else (2, -1))
    rect(im, 5 + la // 2, 17 + bob, 3, 6 - bob, CLOTH[1]); rect(im, 9 + lb // 2, 17 + bob, 3, 6 - bob, CLOTH[0])
    rect(im, 5 + la // 2, 22, 3, 2, BLACK); rect(im, 9 + lb // 2, 22, 3, 2, BLACK)
    # torso armour
    rect(im, 4, 10 + bob, 8, 8, ARMOR[2]); rect(im, 4, 10 + bob, 8, 2, ARMOR[3]); rect(im, 10, 12 + bob, 2, 5, ARMOR[1])
    dither(im, 5, 14 + bob, 3, 3, ARMOR[2], ARMOR[1])
    # head + helmet
    rect(im, 5, 3 + bob, 6, 7, SKIN[2]); rect(im, 5, 3 + bob, 6, 3, ARMOR[3]); rect(im, 4, 5 + bob, 8, 1, ARMOR[2])
    px(im, 7, 7 + bob, BLACK); px(im, 9, 7 + bob, BLACK)                       # eyes
    px(im, 12, 4 + bob, CLOTH[3]); px(im, 12, 3 + bob, CLOTH[3]); px(im, 13, 2 + bob, CLOTH[2])  # plume
    # arm + sword swing
    sw = (frame % 4) - 1
    rect(im, 11, 12 + bob + sw, 2, 3, SKIN[1])
    for i in range(6): px(im, 13 + (i // 3), 9 + bob + sw + i, STONE[4] if i else FIRE[4])
    outline(im, BLACK)
    return im

def slime(frame):
    im = Image.new('RGBA', (16, 16), T)
    sq = frame % 2                                                     # squash & stretch keeps volume
    w, h = 12 + 2 * sq, 9 - sq
    x0, y0 = 8 - w // 2, 16 - h
    for y in range(h):
        r = int(w / 2 * (1 - ((y - h) / h) ** 2) ** 0.5) if y < h - 1 else w // 2
        rect(im, 8 - r, y0 + y, 2 * r, 1, SLIME[2])
    rect(im, x0 + 2, y0 + 1, 3, 2, SLIME[4]); px(im, x0 + 3, y0 + 1, SLIME[4])  # highlight
    dither(im, x0 + 1, 13, w - 2, 2, SLIME[1], SLIME[0])
    px(im, 6, y0 + 3, BLACK); px(im, 10, y0 + 3, BLACK)
    outline(im, BLACK)
    return im

# ---- export: sheet + 8x nearest-neighbour contact sheet
sheet = Image.new('RGBA', (16 * 8, 24 + 16), T)
for i in range(4): sheet.paste(hero(i), (i * 16, 0))
for i in range(2): sheet.paste(slime(i), (64 + i * 16, 4))
sheet.paste(tile_floor(1), (96, 0)); sheet.paste(tile_wall(), (112, 0)); sheet.paste(tile_torch(0), (96, 24 - 8)); sheet.paste(tile_torch(1), (112, 24 - 8))
sheet.save(f'{out}/sheet.png')
big = sheet.resize((sheet.width * 8, sheet.height * 8), Image.NEAREST)
bg = Image.new('RGBA', big.size, (11, 15, 26, 255)); bg.alpha_composite(big); bg.convert('RGB').save(f'{out}/sheet_x8.png')
for i in range(4): hero(i).save(f'{out}/hero_{i}.png')
print('DONE', out)
